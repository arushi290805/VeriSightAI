'use client';

import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import UploadForm from '../components/UploadForm';

export default function DashboardClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectIdParam = searchParams.get('projectId');

  const [projectId, setProjectId] = useState<string | null>(projectIdParam);
  const [projectList, setProjectList] = useState<any[]>([]);
  const [projectInfo, setProjectInfo] = useState<any>(null);
  const [persona, setPersona] = useState('regional_manager');
  const [role, setRole] = useState('regional_manager_apac');
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [telemetry, setTelemetry] = useState<any>(null);
  const [narrative, setNarrative] = useState<any>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);
  const [narrativeError, setNarrativeError] = useState<string | null>(null);
  const [uploadType, setUploadType] = useState('csv');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [adviceFocus, setAdviceFocus] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);
  const [selectedKpi, setSelectedKpi] = useState<string>('');
  const [chartVersion, setChartVersion] = useState<number>(Date.now());
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<{role: 'user'|'llm', text: string}[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    const msg = chatMessage;
    setChatMessage('');
    setChatHistory(prev => [...prev, {role: 'user', text: msg}]);
    setChatLoading(true);

    const formData = new FormData();
    formData.append('message', msg);
    if (projectId) formData.append('project_id', projectId);

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Chat failed');
      setChatHistory(prev => [...prev, {role: 'llm', text: data.response}]);
    } catch (err: any) {
      setChatHistory(prev => [...prev, {role: 'llm', text: 'Error: ' + err.message}]);
    } finally {
      setChatLoading(false);
    }
  };

  const dashboardAbortControllerRef = useRef<AbortController | null>(null);
  const telemetryAbortControllerRef = useRef<AbortController | null>(null);
  const narrativeAbortControllerRef = useRef<AbortController | null>(null);

  const fetchWithTimeout = async (url: string, options: RequestInit = {}, timeoutMs = 20000) => {
    const controller = options.signal ? null : new AbortController();
    const signal = options.signal || controller?.signal;
    const timeoutId = setTimeout(() => {
      if (controller) controller.abort();
    }, timeoutMs);
    try {
      const response = await fetch(url, { ...options, signal: signal || undefined });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  };

  const fetchProjectInfo = async (pid: string) => {
    try {
      const res = await fetchWithTimeout(`http://127.0.0.1:8000/projects/${pid}`);
      if (res.ok) setProjectInfo(await res.json());
    } catch (e) {
      console.error('Failed to fetch project info:', e);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetchWithTimeout('http://127.0.0.1:8000/projects');
      if (res.ok) {
        const data = await res.json();
        setProjectList(data);
        if (!projectId && data.length > 0) {
          setProjectId(data[0].id.toString());
          router.replace(`/dashboard?projectId=${data[0].id}`);
        }
      }
    } catch (e) {
      console.error('Failed to fetch project list:', e);
    }
  };

  const fetchDashboardData = async (pid: string) => {
    if (dashboardAbortControllerRef.current) dashboardAbortControllerRef.current.abort();
    const controller = new AbortController();
    dashboardAbortControllerRef.current = controller;
    setDashboardLoading(true);
    setDashboardError(null);
    try {
      const res = await fetchWithTimeout(
        `http://127.0.0.1:8000/projects/${pid}/dashboard?role=${role}&persona=${persona}`,
        { signal: controller.signal }
      );
      if (!res.ok) throw new Error(`Failed to load dashboard: ${res.statusText}`);
      const json = await res.json();
      setDashboardData(json);
      if (json.charts && Object.keys(json.charts).length > 0) {
        const kpis = Object.keys(json.charts);
        if (!selectedKpi || !json.charts[selectedKpi]) setSelectedKpi(kpis[0]);
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setDashboardError(e.message || 'Error loading dashboard metrics.');
      }
    } finally {
      if (!controller.signal.aborted) setDashboardLoading(false);
    }
  };

  const fetchTelemetry = async () => {
    if (telemetryAbortControllerRef.current) telemetryAbortControllerRef.current.abort();
    const controller = new AbortController();
    telemetryAbortControllerRef.current = controller;
    setTelemetryLoading(true);
    setTelemetryError(null);
    try {
      const res = await fetchWithTimeout('http://127.0.0.1:8000/telemetry/summary', { signal: controller.signal });
      if (!res.ok) throw new Error('Failed to load telemetry summary');
      setTelemetry(await res.json());
    } catch (e: any) {
      if (e.name !== 'AbortError') setTelemetryError('Telemetry error');
    } finally {
      if (!controller.signal.aborted) setTelemetryLoading(false);
    }
  };

  const fetchNarrative = async (pid: string) => {
    if (narrativeAbortControllerRef.current) narrativeAbortControllerRef.current.abort();
    const controller = new AbortController();
    narrativeAbortControllerRef.current = controller;
    setNarrativeLoading(true);
    setNarrativeError(null);
    try {
      const res = await fetchWithTimeout(
        `http://127.0.0.1:8000/projects/${pid}/narrative?role=${role}&persona=${persona}`,
        { signal: controller.signal },
        40000
      );
      if (!res.ok) throw new Error('Failed to fetch narrative');
      setNarrative(await res.json());
    } catch (e: any) {
      if (e.name !== 'AbortError') setNarrativeError(e.message || 'Failed to load narrative.');
    } finally {
      if (!controller.signal.aborted) setNarrativeLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    return () => {
      dashboardAbortControllerRef.current?.abort();
      telemetryAbortControllerRef.current?.abort();
      narrativeAbortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (projectIdParam) setProjectId(projectIdParam);
  }, [projectIdParam]);

  useEffect(() => {
    if (projectId) {
      fetchProjectInfo(projectId);
      Promise.all([fetchDashboardData(projectId), fetchTelemetry()]);
      fetchNarrative(projectId);
    }
  }, [projectId, persona, role]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !projectId) return;
    setUploadLoading(true);
    setUploadStatus('Uploading. Spreadsheets are summarized before they hit the dashboard, so this should stay snappy.');

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('project_id', projectId);
    formData.append('advice_focus', adviceFocus);
    const url = uploadType === 'csv'
      ? 'http://127.0.0.1:8000/upload/csv'
      : 'http://127.0.0.1:8000/upload/screenshot';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 180000);
    try {
      const res = await fetch(url, { method: 'POST', body: formData, signal: controller.signal });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Upload failed');
      setUploadStatus(data.message || 'Upload finished.');
      setUploadFile(null);
      setChartVersion(Date.now());
      fetchProjectInfo(projectId);
      fetchDashboardData(projectId);
      fetchTelemetry();
      fetchNarrative(projectId);
    } catch (err: any) {
      setUploadStatus('Upload did not complete: ' + (err.name === 'AbortError' ? 'timed out' : err.message));
    } finally {
      clearTimeout(timeout);
      setUploadLoading(false);
    }
  };

  const analysis = dashboardData?.analysis || projectInfo?.analysis;
  const uploadPanel = (
    <div className="card">
      <h3 className="text-lg mb-3">Add data</h3>
      <UploadForm
        projectId={projectId || ''}
        uploadType={uploadType}
        setUploadType={setUploadType}
        adviceFocus={adviceFocus}
        setAdviceFocus={setAdviceFocus}
        file={uploadFile}
        setFile={setUploadFile}
        loading={uploadLoading}
        status={uploadStatus}
        onSubmit={handleUpload}
        compact
      />
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl mb-1">{projectInfo?.name || 'Dashboard'}</h1>
          <p className="text-[var(--muted)] text-sm">{projectInfo?.description}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <select
            className="field w-auto"
            value={projectId || ''}
            onChange={e => {
              setProjectId(e.target.value);
              router.push(`/dashboard?projectId=${e.target.value}`);
            }}
          >
            {projectList.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select className="field w-auto" value={persona} onChange={e => setPersona(e.target.value)}>
            <option value="regional_manager">Operator view</option>
            <option value="cfo">Finance view</option>
          </select>
          <select className="field w-auto" value={role} onChange={e => setRole(e.target.value)}>
            <option value="regional_manager_apac">APAC access</option>
            <option value="global_cfo">Global access</option>
          </select>
        </div>
      </div>

      {dashboardLoading && !dashboardData ? (
        <p className="text-[var(--muted)]">Loading charts…</p>
      ) : dashboardError ? (
        <div className="card">
          <p className="mb-3">{dashboardError}</p>
          <button className="btn" onClick={() => projectId && fetchDashboardData(projectId)}>Try again</button>
        </div>
      ) : dashboardData?.empty ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 card">
            <h2 className="text-2xl mb-2">Nothing here yet</h2>
            <p className="text-[var(--muted)]">Upload a CSV or a screenshot. Ask a question such as “what drives sales” rather than naming columns.</p>
          </div>
          {uploadPanel}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="card">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <h2 className="text-xl">Trend</h2>
                <div className="flex flex-wrap gap-2">
                  {dashboardData?.charts && Object.keys(dashboardData.charts).map((kpi) => (
                    <button
                      key={kpi}
                      onClick={() => setSelectedKpi(kpi)}
                      className={`text-sm px-2 py-1 border rounded ${
                        selectedKpi === kpi ? 'border-[var(--moss)] bg-[var(--moss-soft)]' : 'border-[var(--line)]'
                      }`}
                    >
                      {kpi}
                    </button>
                  ))}
                </div>
              </div>
              {selectedKpi && dashboardData?.charts?.[selectedKpi] ? (
                <img
                  src={`http://127.0.0.1:8000${dashboardData.charts[selectedKpi]}?t=${chartVersion}`}
                  alt={`${selectedKpi} trend`}
                  className="w-full h-auto"
                />
              ) : (
                <p className="text-[var(--muted)] text-sm">No trend chart for this metric yet.</p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {dashboardData?.metrics && Object.entries(dashboardData.metrics).map(([kpiName, val]: any) => (
                <div key={kpiName} className="card">
                  <p className="text-sm text-[var(--muted)]">{kpiName}</p>
                  <p className="text-2xl mt-1">{Number(val.current_value).toLocaleString()}</p>
                  <p className="text-xs text-[var(--muted)] mt-2">
                    Baseline {Number(val.baseline_value).toFixed(1)} · {val.is_anomaly ? 'unusual' : 'in range'}
                  </p>
                </div>
              ))}
            </div>

            {analysis && (
              <div className="card space-y-4">
                <h2 className="text-xl">How the fields relate</h2>
                {analysis.advice_focus && (
                  <p className="text-sm">Advice requested: {analysis.advice_focus}</p>
                )}
                {analysis.target && (
                  <p className="text-sm">Primary metric: <strong>{analysis.target}</strong></p>
                )}
                {analysis.formulas?.length > 0 && (
                  <div>
                    <p className="label">Detected calculations</p>
                    <ul className="text-sm space-y-1">
                      {analysis.formulas.map((f: any, i: number) => (
                        <li key={i}>{f.result} ≈ {f.expression}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {analysis.correlations?.length > 0 && (
                  <div>
                    <p className="label">Correlation with {analysis.target}</p>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-[var(--muted)]">
                          <th className="py-1">Field</th>
                          <th>r</th>
                          <th>Strength</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.correlations.map((c: any) => (
                          <tr key={c.field} className="border-t border-[var(--line)]">
                            <td className="py-1">{c.field}</td>
                            <td>{c.correlation}</td>
                            <td>{c.strength} {c.direction}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {analysis.categorical_drivers?.length > 0 && (
                  <div>
                    <p className="label">Segments that move the metric</p>
                    <ul className="text-sm space-y-2">
                      {analysis.categorical_drivers.map((d: any) => (
                        <li key={d.field}>
                          {d.field}: {d.top_segments?.map((s: any) => `${s.label} (${s.mean})`).join(', ')}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {analysis.notes?.length > 0 && (
                  <ul className="text-sm list-disc pl-4">
                    {analysis.notes.map((n: string, i: number) => <li key={i}>{n}</li>)}
                  </ul>
                )}
              </div>
            )}

            <div className="card">
              <h2 className="text-xl mb-4">Written take</h2>
              {narrativeLoading ? (
                <p className="text-[var(--muted)]">Writing the summary…</p>
              ) : narrativeError ? (
                <div>
                  <p className="mb-2">{narrativeError}</p>
                  <button className="btn" onClick={() => projectId && fetchNarrative(projectId)}>Retry</button>
                </div>
              ) : narrative?.error ? (
                <p>{narrative.error}</p>
              ) : persona === 'cfo' ? (
                <p className="leading-relaxed">{narrative?.narrative || 'No summary yet.'}</p>
              ) : (
                <div className="space-y-4">
                  <p className="text-lg">{narrative?.kpi_summary || 'No summary yet.'}</p>
                  <p className="leading-relaxed text-[var(--ink)]">{narrative?.executive_summary}</p>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="border border-[var(--line)] p-3 rounded">
                      <p className="label">Magnitude</p>
                      <p>{narrative?.magnitude || '—'}</p>
                    </div>
                    <div className="border border-[var(--line)] p-3 rounded">
                      <p className="label">Confidence</p>
                      <p>{narrative?.confidence || '—'}</p>
                    </div>
                  </div>
                  {narrative?.recommended_actions && (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-[var(--muted)]">
                          <th className="py-2">Driver</th>
                          <th>Action</th>
                          <th>Impact</th>
                        </tr>
                      </thead>
                      <tbody>
                        {narrative.recommended_actions.map((act: any, i: number) => (
                          <tr key={i} className="border-t border-[var(--line)]">
                            <td className="py-2">{act.driver}</td>
                            <td>{act.action}</td>
                            <td>{act.expected_impact}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>

            <div className="card">
              <h2 className="text-xl mb-4">Evidence</h2>
              {dashboardData?.hypotheses?.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No unusual movements logged.</p>
              ) : dashboardData?.hypotheses?.map((h: any, i: number) => (
                <div key={i} className="mb-5 last:mb-0">
                  <div className="flex justify-between gap-3 mb-2">
                    <h3 className="text-base">{h.description}</h3>
                    <span className="text-xs">{h.confidence_tier}</span>
                  </div>
                  <p className="text-xs text-[var(--muted)] mb-2">{h.label}</p>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-[var(--muted)]">
                        <th className="py-1">Source</th>
                        <th>Method</th>
                        <th>Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {h.evidence_items.map((ev: any, j: number) => (
                        <tr key={j} className="border-t border-[var(--line)]">
                          <td className="py-1">{ev.source}</td>
                          <td>{ev.method}</td>
                          <td>{ev.contribution_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            {uploadPanel}
            <div className="card flex flex-col" style={{ maxHeight: '600px' }}>
              <h2 className="text-lg mb-3">Operator Chat</h2>
              <div className="flex-grow overflow-y-auto mb-3 space-y-3 p-2 border border-[var(--line)] rounded" style={{ minHeight: '200px' }}>
                {chatHistory.length === 0 ? (
                  <p className="text-sm text-[var(--muted)]">Ask the LLM for suggestions...</p>
                ) : (
                  chatHistory.map((chat, idx) => (
                    <div key={idx} className={`p-2 rounded text-sm ${chat.role === 'user' ? 'bg-[var(--moss-soft)] ml-4' : 'bg-[var(--background)] border border-[var(--line)] mr-4'}`}>
                      <strong>{chat.role === 'user' ? 'You' : 'LLM'}: </strong>
                      <span className="whitespace-pre-wrap">{chat.text}</span>
                    </div>
                  ))
                )}
                {chatLoading && <p className="text-sm text-[var(--muted)]">Thinking...</p>}
              </div>
              <form onSubmit={handleChat} className="flex gap-2">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  placeholder="Ask for suggestions..."
                  className="field flex-grow"
                  disabled={chatLoading}
                />
                <button type="submit" className="btn" disabled={chatLoading || !chatMessage.trim()}>Send</button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
