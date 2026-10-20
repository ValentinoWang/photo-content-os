// Independent observed-value checks consumed by the browser capture gate.
export function expectedShots(data){
 const statuses=['selected','usable','unused','rejected'];
 const counts=Object.fromEntries(statuses.map(k=>[k,data.shots.filter(s=>s.status===k).length]));
 const duration=data.shots.filter(s=>s.status==='selected').reduce((a,s)=>a+(s.kind==='photo'?2.5:s.duration_sec||0),0);
 return {counts,duration,concluded:data.shots.filter(s=>statuses.includes(s.status)).length};
}
export function compareNumbers(observed,expected){
 const failures=[];
 for(const [key,value] of Object.entries(expected))if(observed[key]!==value)failures.push({key,observed:observed[key],expected:value});
 return failures;
}
