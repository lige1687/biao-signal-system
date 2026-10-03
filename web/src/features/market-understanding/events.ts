export const calendarSource='https://www.bls.gov/schedule/2026/home.htm';
export const calendarVerified='2026-10-03';
export interface MarketEvent {name:string;period:string;at:string;source:string}
// Public release schedule facts, not a historical as-of dataset or automatic refreshed feed.
export const marketEvents:MarketEvent[]=[
 ['2026-01-13T13:30:00Z','美国CPI','2025-12'],['2026-03-11T12:30:00Z','美国CPI','2026-02'],['2026-05-12T12:30:00Z','美国CPI','2026-04'],['2026-06-10T12:30:00Z','美国CPI','2026-05'],['2026-07-14T12:30:00Z','美国CPI','2026-06'],['2026-08-12T12:30:00Z','美国CPI','2026-07'],['2026-09-11T12:30:00Z','美国CPI','2026-08'],['2026-10-02T12:30:00Z','美国就业报告','2026-09'],['2026-10-14T12:30:00Z','美国CPI','2026-09'],['2026-10-15T12:30:00Z','美国PPI','2026-09'],
].map(([at,name,period])=>({at,name,period,source:calendarSource}));
export function localEventTime(at:string,zone:string){return new Intl.DateTimeFormat('sv-SE',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(at));}
export function eventDate(at:string){return localEventTime(at,'America/New_York').slice(0,10);}
export function calendarExpired(today:string){return today>'2026-10-31';}
export function upcomingEvents(now:string){return marketEvents.filter(e=>Date.parse(e.at)>Date.parse(now));}
