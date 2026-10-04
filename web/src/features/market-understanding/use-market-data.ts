import {loadContext} from './context-model';
import {useQuery} from '@tanstack/react-query';
import {loadHistory,shanghaiToday,type Market} from './dashboard-model';
import {decodeIndices} from './comparison-model';
export function useMarketData(market:Market,withIndices=false){
 const rates=useQuery({queryKey:['market-dashboard','rates'],queryFn:({signal})=>loadHistory('rates',signal),staleTime:300_000,retry:false});
 const macro=useQuery({queryKey:['market-dashboard',market==='cn'?'macro':'usMacro'],queryFn:({signal})=>loadHistory(market==='cn'?'macro':'usMacro',signal),staleTime:300_000,retry:false});
 const context=useQuery({queryKey:['market-context',1],queryFn:({signal})=>loadContext(signal),staleTime:300_000,retry:false});
 const indices=useQuery({queryKey:['market-index-comparison',20],queryFn:async({signal})=>{const r=await fetch('/api/fundamentals/overlay-history?years=20',{signal});if(!r.ok)throw new Error(`指数资料暂不可用（${r.status}）`);return decodeIndices(await r.json(),shanghaiToday());},enabled:withIndices,staleTime:12*3600_000,retry:false});
 return {series:{...rates.data?.series,...macro.data?.series,...context.data?.series},indices:indices.data??{},gaps:context.data?.gaps??{},contextUnavailable:context.isError,pending:rates.isLoading||macro.isLoading||context.isLoading||(withIndices&&indices.isLoading),failed:rates.isError||macro.isError||context.isError||(withIndices&&indices.isError),retry:()=>{void rates.refetch();void macro.refetch();void context.refetch();if(withIndices)void indices.refetch();}};
}
