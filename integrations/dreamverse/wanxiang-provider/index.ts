import { createHash, randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { mkdir, open, readFile, rename, unlink } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { join } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-connection'
import type {} from '@dv/ffmpeg'
import type { ModelEntry, RenderModelFacts, RenderRequest } from '@dv/models'

// The runtime checkout owns Schemastery. The profile entry is a symlink to this
// repository, outside the runtime's node_modules lookup chain.
const runtimeRequire = createRequire(join(process.cwd(), 'packages/dv/fastvideo/package.json'))
const z = runtimeRequire('@deepseek-ai/schemastery') as typeof import('@deepseek-ai/schemastery').default

export const name = 'dv-wanxiang-provider'
export const inject = ['dvModels', 'dvAssetPool', 'dvFfmpeg']
interface Settings { baseUrl: string; stateDir: string; maxSubmissions?: number }
export const Config = z.object({
  baseUrl: z.string().required(),
  stateDir: z.string().required(),
  maxSubmissions: z.natural().min(1),
})

const facts = JSON.parse(readFileSync(new URL('./model-facts.json', import.meta.url), 'utf8')) as
  RenderModelFacts & { frameSizes: Record<string, Record<string, [number, number]>> }
const promptSkill = readFileSync(new URL('./skills/wanxiang-shot.md', import.meta.url), 'utf8')
const keyPattern = /^[a-f0-9]{64}$/
const idPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
const cloudStatuses = new Set(['PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELED', 'UNKNOWN', 'SUSPENDED'])

interface Shot {
  project: string
  shot_id: string
  prompt: string
  model: string
  seconds: number
  aspect_ratio: string
  resolution: string
}
interface Receipt {
  status: 'submitting' | 'submitted' | 'unknown' | 'rejected'
  spec_hash: string
  task_id?: string
  submit_http_status?: number
  submit_error_code?: string
}
interface WanResponse {
  code?: string
  output?: { task_id?: string; task_status?: string; video_url?: string }
  usage?: { duration?: number; output_video_duration?: number; video_duration?: number }
}

function validSpec(shot: Shot): boolean {
  return shot.model === facts.modelId && typeof shot.prompt === 'string' && shot.prompt.trim() !== ''
    && [...shot.prompt].length <= 1500 && facts.durationsSec?.includes(shot.seconds) === true
    && facts.aspectRatios.includes(shot.aspect_ratio) && facts.resolutions.includes(shot.resolution)
}

function digest(parts: unknown[]): string {
  return createHash('sha256').update(JSON.stringify(parts)).digest('hex')
}

function specHash(shot: Pick<Shot, 'model' | 'seconds' | 'aspect_ratio' | 'resolution' | 'prompt'>): string {
  return digest([shot.model, shot.seconds, shot.aspect_ratio, shot.resolution, shot.prompt])
}

function shotSeed(key: string): number {
  return Number.parseInt(key.slice(0, 7), 16)
}

function isExists(error: unknown): boolean {
  return (error as NodeJS.ErrnoException).code === 'EEXIST'
}

async function writeRecord(path: string, value: object, exclusive: boolean): Promise<void> {
  const target = exclusive ? path : path + '.' + randomUUID()
  const file = await open(target, 'wx', 0o600)
  try {
    try {
      await file.writeFile(JSON.stringify(value) + '\n')
      await file.sync()
    } finally {
      await file.close()
    }
    if (!exclusive) await rename(target, path)
  } finally {
    if (!exclusive) await unlink(target).catch(() => {})
  }
}

function providerKey(): string {
  const key = process.env.DV_WAN_API_KEY
  if (!key) throw new Error('Wan service credential is unavailable.')
  return key
}

export function apply(ctx: Context, config: Settings) {
  const origin = new URL(config.baseUrl)
  if (origin.protocol !== 'https:' || origin.username || origin.password
      || origin.pathname !== '/' || origin.search || origin.hash
      || !origin.hostname.endsWith('.aliyuncs.com')) {
    throw new Error('Configure an HTTPS Aliyun DashScope origin.')
  }
  const receiptPath = (key: string) => join(config.stateDir, key + '.json')
  const readReceipt = async (key: string): Promise<Receipt | undefined> => {
    try {
      return JSON.parse(await readFile(receiptPath(key), 'utf8')) as Receipt
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
      return undefined
    }
  }
  const replyReceipt = (receipt: Receipt | undefined, status = 200) =>
    Response.json({
      status: receipt?.status ?? 'missing', task_id: receipt?.task_id,
      submit_http_status: receipt?.submit_http_status, submit_error_code: receipt?.submit_error_code,
    }, { status })
  const requestSignal = (signal?: AbortSignal) =>
    AbortSignal.any([AbortSignal.timeout(45_000), ...(signal === undefined ? [] : [signal])])

  async function reserveBudget(key: string): Promise<boolean> {
    if (config.maxSubmissions === undefined) return true
    for (let slot = 1; slot <= config.maxSubmissions; slot += 1) {
      try {
        await writeRecord(join(config.stateDir, 'submission-' + slot + '.json'), { key }, true)
        return true
      } catch (error) {
        if (!isExists(error)) throw error
      }
    }
    return false
  }

  async function pollTask(id: string, signal?: AbortSignal): Promise<WanResponse> {
    const response = await fetch(new URL('/api/v1/tasks/' + encodeURIComponent(id), origin), {
      headers: { Authorization: 'Bearer ' + providerKey() }, signal: requestSignal(signal), redirect: 'error',
    })
    if (!response.ok) throw new Error('Wan status request failed (HTTP ' + response.status + ').')
    const body = await response.json() as WanResponse
    if (!body.output?.task_status || !cloudStatuses.has(body.output.task_status)
        || (body.output.task_id !== undefined && body.output.task_id !== id)) {
      throw new Error('Wan returned an unreadable task status.')
    }
    return body
  }

  async function submit(key: string, shot: Shot): Promise<Response> {
    const hash = specHash(shot)
    if (!validSpec(shot) || typeof shot.project !== 'string' || !idPattern.test(shot.project)
        || typeof shot.shot_id !== 'string' || !idPattern.test(shot.shot_id)
        || key !== digest([shot.project, shot.shot_id, hash])) {
      return Response.json({ code: 'invalid_confirmation' }, { status: 400 })
    }
    const credential = providerKey()
    await mkdir(config.stateDir, { recursive: true, mode: 0o700 })
    const path = receiptPath(key)
    const receipt: Receipt = { status: 'submitting', spec_hash: hash }
    try {
      await writeRecord(path, receipt, true)
    } catch (error) {
      if (!isExists(error)) throw error
      return replyReceipt(await readReceipt(key))
    }
    if (!await reserveBudget(key)) {
      receipt.status = 'rejected'
      await writeRecord(path, receipt, false)
      return replyReceipt(receipt)
    }

    const size = facts.frameSizes[shot.aspect_ratio][shot.resolution].join('*')
    try {
      const response = await fetch(new URL('/api/v1/services/aigc/video-generation/video-synthesis', origin), {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + credential, 'Content-Type': 'application/json', 'X-DashScope-Async': 'enable' },
        body: JSON.stringify({
          model: shot.model, input: { prompt: shot.prompt },
          parameters: {
            size, duration: shot.seconds, seed: shotSeed(key),
            shot_type: 'single', prompt_extend: true, watermark: false,
          },
        }),
        signal: requestSignal(),
        redirect: 'error',
      })
      receipt.submit_http_status = response.status
      const body = await response.json() as WanResponse
      const id = body.output?.task_id
      if (response.ok && typeof id === 'string' && idPattern.test(id) && !id.includes(credential)) {
        receipt.status = 'submitted'
        receipt.task_id = id
      } else {
        receipt.status = 'unknown'
        if (typeof body.code === 'string' && /^[A-Za-z][A-Za-z0-9_.-]{0,79}$/.test(body.code)
            && !body.code.includes(credential)) receipt.submit_error_code = body.code
      }
    } catch {
      receipt.status = 'unknown'
    }
    // No polling happens until this durable receipt is returned to the bridge.
    await writeRecord(path, receipt, false)
    return replyReceipt(receipt)
  }

  ctx.inject(['connection'], (connected) => {
    const routes = ['submit', 'receipt', 'status'] as const
    for (const action of routes) {
      connected.effect(() => {
        const dispose = connected.connection.fetch.register({
          path: '/api/dv/wanxiang/' + action, methods: ['POST'], requestBody: 'buffered',
          async fetch(request) {
            try {
              const body = await request.json() as Shot & { key: string; task_id?: string }
              if (typeof body?.key !== 'string' || !keyPattern.test(body.key)) {
                return Response.json({ code: 'invalid_confirmation' }, { status: 400 })
              }
              if (action === 'submit') return await submit(body.key, body)
              const receipt = await readReceipt(body.key)
              if (action === 'receipt') return replyReceipt(receipt)
              if (receipt?.task_id === undefined || receipt.task_id !== body.task_id) {
                return Response.json({ code: 'task_receipt_mismatch' }, { status: 409 })
              }
              const result = await pollTask(receipt.task_id)
              const usage = result.usage?.duration ?? result.usage?.output_video_duration ?? result.usage?.video_duration
              return Response.json({
                task_id: receipt.task_id, status: result.output?.task_status,
                billed_video_seconds: typeof usage === 'number' && Number.isFinite(usage) && usage >= 0 ? usage : null,
              })
            } catch {
              // Provider response bodies and signed URLs are never returned or logged.
              return Response.json({ code: 'wan_' + action + '_unavailable' }, { status: 502 })
            }
          },
        })
        return () => { void dispose() }
      }, 'Wanxiang ' + action)
    }
  })

  const requestSpec = (request: RenderRequest) => ({
    model: facts.modelId, prompt: request.prompt, seconds: request.durationSec ?? 0,
    aspect_ratio: request.aspectRatio ?? '', resolution: request.resolution ?? '',
  })
  const entry: ModelEntry<'t2v'> = {
    modality: 'video', task: 't2v', provider: 'wanxiang', model: facts.modelId,
    description: 'Wan 2.6 text-to-video for a continuous shot, with no reference frames. The production desk confirms and submits the shot, then DreamVerse materializes it. Ending local monitoring does not cancel the cloud task.',
    promptSkill: { name: 'wanxiang-shot', description: 'Write a Wan 2.6 text-to-video prompt.', content: promptSkill },
    async facts() { return facts },
    async schema() {
      return {
        duration_sec: { min: facts.minDurationSec, max: facts.maxDurationSec },
        aspect_ratios: facts.aspectRatios, resolutions: facts.resolutions,
        inputs: { reference: { min: 0, max: 0 }, first_frame: { min: 0, max: 0 }, last_frame: { min: 0, max: 0 } },
        extra: { bridge_confirmation: { type: 'string', description: 'Confirmation key issued by the production desk for this shot.' } },
        cancellation: 'monitoring_only',
      }
    },
    async validateGenerationRequest(request: RenderRequest) {
      const errors: string[] = []
      if (request.references.length || request.firstFrame || request.lastFrame) errors.push('Wan 2.6 uses a text prompt without reference or frame assets.')
      if (!validSpec(requestSpec(request))) errors.push('Choose a listed duration, aspect ratio and resolution, and supply a prompt of 1–1500 characters.')
      const key = request.extra.bridge_confirmation
      if (Object.keys(request.extra).length !== 1 || typeof key !== 'string' || !keyPattern.test(key)) {
        errors.push('Use the production desk confirmation key for this shot.')
      } else if (request.seed !== shotSeed(key)) {
        errors.push('Use the seed assigned by the production desk for this shot.')
      }
      return errors
    },
    async *render(request: RenderRequest, signal?: AbortSignal) {
      const problems = await entry.validateGenerationRequest(request)
      if (problems.length > 0) throw new Error(problems.join(' '))
      const receipt = await readReceipt(request.extra.bridge_confirmation as string)
      if (!receipt?.task_id || receipt.spec_hash !== specHash(requestSpec(request))) {
        throw new Error('No confirmed Wan task matches this shot specification.')
      }
      const result = await pollTask(receipt.task_id, signal)
      const url = result.output?.video_url
      if (result.output?.task_status !== 'SUCCEEDED' || typeof url !== 'string') {
        throw new Error('The confirmed Wan task has no available video.')
      }
      let video: Buffer
      try {
        const assetUrl = new URL(url)
        if (assetUrl.protocol !== 'https:' || !assetUrl.hostname.endsWith('.aliyuncs.com')
            || assetUrl.username || assetUrl.password) throw new Error()
        const media = await fetch(assetUrl, { signal: requestSignal(signal), redirect: 'error' })
        if (!media.ok) throw new Error()
        video = Buffer.from(await media.arrayBuffer())
      } catch {
        signal?.throwIfAborted()
        throw new Error('Wan video download failed.')
      }
      const png = await ctx.dvFfmpeg.lastFrame(video)
      signal?.throwIfAborted()
      yield { kind: 'last_frame', png }
      yield { kind: 'video_start', mime: 'video/mp4' }
      yield { kind: 'chunk', bytes: video }
      yield { kind: 'done', timings: {} }
    },
  }
  ctx.effect(() => ctx.dvModels.register(entry), 'Wanxiang Wan 2.6')
}
