'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function Dashboard() {
  const [scenario, setScenario] = useState('multi_factor');
  const [persona, setPersona] = useState('regional_manager');
  const [role, setRole] = useState('regional_manager_apac');
  
  const [data, setData] = useState<any>(null);
  const [metadata, setMetadata] = useState<any>(null);
  const [telemetry, setTelemetry] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/scenarios/${scenario}?role=${role}&persona=${persona}`);
      const json = await res.json();
      setData(json);
      
      const metaRes = await fetch('http://127.0.0.1:8000/metadata/tags');
      setMetadata(await metaRes.json());
      
      const telRes = await fetch('http://127.0.0.1:8000/telemetry/summary');
      setTelemetry(await telRes.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchDashboard();
  }, [scenario, persona, role]);

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto space-y-8 text-slate-800">
      
      {/* HEADER CONTROLS */}
      <div className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">VeriSight AI</h1>
        <div className="flex gap-4 mt-4 md:mt-0">
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-slate-500 uppercase">Scenario</label>
            <select className="mt-1 border-slate-300 rounded-md p-2 bg-slate-50" value={scenario} onChange={e => setScenario(e.target.value)}>
              <option value="multi_factor">Multi-factor Revenue Drop</option>
              <option value="sparse_history">Sparse-history Churn KPI</option>
              <option value="ambiguous">Ambiguous Case</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-slate-500 uppercase">Persona</label>
            <select className="mt-1 border-slate-300 rounded-md p-2 bg-slate-50" value={persona} onChange={e => setPersona(e.target.value)}>
              <option value="regional_manager">Regional Manager</option>
              <option value="cfo">CFO</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-slate-500 uppercase">Security Role</label>
            <select className="mt-1 border-slate-300 rounded-md p-2 bg-slate-50" value={role} onChange={e => setRole(e.target.value)}>
              <option value="regional_manager_apac">Regional Manager (APAC)</option>
              <option value="global_cfo">Global CFO</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-500 animate-pulse">Loading evidence...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* MAIN NARRATIVE */}
          <div className="col-span-2 space-y-8">
            <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
              <h2 className="text-2xl font-semibold mb-6 border-b pb-4">KPI Narrative (LLM-Synthesized)</h2>
              
              {data?.narrative?.error ? (
                <div className="p-4 bg-red-50 text-red-700 rounded-lg">
                  <strong>API Error:</strong> {data.narrative.error}
                  <p className="mt-2 text-sm">Please configure GEMINI_API_KEYS in .env to generate narratives.</p>
                </div>
              ) : persona === 'cfo' ? (
                <p className="text-lg leading-relaxed text-slate-700">
                  {data?.narrative?.narrative || 'No narrative generated.'}
                </p>
              ) : (
                <div className="space-y-6">
                  <div>
                    <h3 className="font-bold text-slate-500 text-sm uppercase tracking-wider">KPI Summary</h3>
                    <p className="text-xl font-medium mt-1">{data?.narrative?.kpi_summary}</p>
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-500 text-sm uppercase tracking-wider">Executive Summary</h3>
                    <p className="text-slate-700 mt-1">{data?.narrative?.executive_summary}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-50 p-4 rounded-lg">
                      <h3 className="font-bold text-slate-500 text-xs uppercase">Magnitude</h3>
                      <p className="text-lg font-semibold">{data?.narrative?.magnitude}</p>
                    </div>
                    <div className="bg-slate-50 p-4 rounded-lg">
                      <h3 className="font-bold text-slate-500 text-xs uppercase">Confidence</h3>
                      <p className="text-lg font-semibold">{data?.narrative?.confidence}</p>
                    </div>
                  </div>
                  
                  {data?.narrative?.recommended_actions && (
                    <div>
                      <h3 className="font-bold text-slate-500 text-sm uppercase tracking-wider mb-3">Recommended Actions</h3>
                      <div className="overflow-x-auto rounded-lg border">
                        <table className="min-w-full text-sm text-left">
                          <thead className="bg-slate-100 text-slate-600">
                            <tr>
                              <th className="px-4 py-3 font-semibold">Driver</th>
                              <th className="px-4 py-3 font-semibold">Action</th>
                              <th className="px-4 py-3 font-semibold">Impact</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y">
                            {data.narrative.recommended_actions.map((act: any, i: number) => (
                              <tr key={i} className="hover:bg-slate-50">
                                <td className="px-4 py-3">{act.driver}</td>
                                <td className="px-4 py-3">{act.action}</td>
                                <td className="px-4 py-3 text-green-700 font-medium">{act.expected_impact}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* EVIDENCE LEDGER */}
            <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
              <h2 className="text-2xl font-semibold mb-6 border-b pb-4">Evidence Ledger</h2>
              {data?.hypotheses?.map((h: any, i: number) => (
                <div key={i} className="mb-8 last:mb-0">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium">{h.description}</h3>
                    <span className={`px-3 py-1 text-xs font-bold rounded-full ${
                      h.confidence_tier === 'HIGH' ? 'bg-green-100 text-green-800' :
                      h.confidence_tier === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                      h.confidence_tier === 'AMBIGUOUS' ? 'bg-purple-100 text-purple-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {h.confidence_tier}
                    </span>
                  </div>
                  <div className="text-sm text-slate-500 mb-4 flex gap-4">
                    <span><strong>Label:</strong> {h.label}</span>
                    <span><strong>Z-Score:</strong> {h.z_score_associated || 'N/A'}</span>
                  </div>
                  <div className="overflow-x-auto rounded-lg border">
                    <table className="min-w-full text-sm text-left">
                      <thead className="bg-slate-100 text-slate-600">
                        <tr>
                          <th className="px-4 py-2">Source</th>
                          <th className="px-4 py-2">Method</th>
                          <th className="px-4 py-2">Weight</th>
                          <th className="px-4 py-2">Temporal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {h.evidence_items.map((ev: any, j: number) => (
                          <tr key={j} className="hover:bg-slate-50">
                            <td className="px-4 py-2 font-mono text-xs">{ev.source}</td>
                            <td className="px-4 py-2">{ev.method}</td>
                            <td className="px-4 py-2">{ev.contribution_pct}%</td>
                            <td className="px-4 py-2">
                              {ev.is_temporal_precedent ? <span className="text-green-600">Yes</span> : <span className="text-slate-400">No</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* SIDEBAR */}
          <div className="space-y-8">
            
            {/* TELEMETRY */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <h2 className="text-xl font-semibold mb-4 border-b pb-2">Session Telemetry</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-slate-500 uppercase text-xs font-bold">Total Cost</div>
                  <div className="text-lg font-semibold text-emerald-600">${telemetry?.total_cost_usd?.toFixed(6) || 0}</div>
                </div>
                <div>
                  <div className="text-slate-500 uppercase text-xs font-bold">LLM Calls</div>
                  <div className="text-lg font-semibold">{telemetry?.total_llm_calls || 0}</div>
                </div>
                <div>
                  <div className="text-slate-500 uppercase text-xs font-bold">Tokens In</div>
                  <div className="text-lg font-semibold">{telemetry?.total_tokens_in || 0}</div>
                </div>
                <div>
                  <div className="text-slate-500 uppercase text-xs font-bold">Tokens Out</div>
                  <div className="text-lg font-semibold">{telemetry?.total_tokens_out || 0}</div>
                </div>
                <div className="col-span-2">
                  <div className="text-slate-500 uppercase text-xs font-bold">Avg Latency</div>
                  <div className="text-lg font-semibold">{telemetry?.average_latency_ms?.toFixed(0) || 0} ms</div>
                </div>
              </div>
            </div>

            {/* METADATA TAGS */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <h2 className="text-xl font-semibold mb-4 border-b pb-2">System Architecture</h2>
              <div className="space-y-3">
                {metadata?.tags?.map((tag: any, i: number) => (
                  <div key={i} className="text-sm p-3 rounded-lg border bg-slate-50 flex flex-col gap-1">
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-semibold">{tag.function}</span>
                      <span className={`text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider ${
                        tag.type === 'DETERMINISTIC' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                      }`}>
                        {tag.type}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500 truncate">{tag.file}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
