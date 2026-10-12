// Local, offline Chinese glyph verification using the operating system's Vision OCR.
import Foundation
import Vision

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true
let handler = VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1]))
try handler.perform([request])
let lines = (request.results ?? []).flatMap { $0.topCandidates(5).map { $0.string } }
let data = try JSONSerialization.data(withJSONObject: lines)
print(String(data: data, encoding: .utf8)!)
