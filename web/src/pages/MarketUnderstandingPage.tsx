import IndexComparison from '../features/market-understanding/IndexComparison';
import MarketDashboard from "../features/market-understanding/MarketDashboard";
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import FundamentalsPage from './FundamentalsPage';
import { legacyFundamentalsTarget, marketSectionFromHash, marketSections } from '../features/market-understanding/navigation';

export function LegacyFundamentalsRedirect() {
  const location=useLocation();
  return <Navigate replace to={legacyFundamentalsTarget(location.search,location.hash)}/>;
}

export default function MarketUnderstandingPage() {
  const location=useLocation(),navigate=useNavigate();
  const section=marketSectionFromHash(location.hash);
  return <div className="mu-unified">
    <header className="mu-unified-heading"><h1>市场理解</h1><p>宏观、资金、估值与市场状态</p></header>
    <nav className="mu-unified-nav" aria-label="市场理解分区">{marketSections.map(s=><button key={s.id} aria-pressed={section===s.id} onClick={()=>navigate({pathname:'/market-understanding',search:location.search,hash:`#${s.id}`})}>{s.label}</button>)}</nav>
    {section!=='overview' && <p className="mu-unified-note">{marketSections.find(s=>s.id===section)?.note}</p>}
    {section==='index-comparison'?<IndexComparison/>:section==='overview'?<MarketDashboard embedded/>:<FundamentalsPage key={section} section={section}/>}
  </div>;
}
