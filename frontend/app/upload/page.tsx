'use client'

import { useState, useEffect } from 'react'
import UploadForm from '../components/UploadForm'
import { API_BASE } from '../../lib/config'

export default function UploadPage() {
  const [projects, setProjects] = useState<any[]>([])
  const [selectedProject, setSelectedProject] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [type, setType] = useState('csv')
  const [adviceFocus, setAdviceFocus] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const res = await fetch(`${API_BASE}/projects`)
        if (res.ok) {
          const data = await res.json()
          setProjects(data)
          if (data.length > 0) setSelectedProject(data[0].id.toString())
        }
      } catch (e) {
        console.error(e)
      }
    }
    fetchProjects()
  }, [])

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !selectedProject) return
    setLoading(true)
    setStatus('Reading the file. Large spreadsheets are aggregated first so this should not hang.')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('project_id', selectedProject)
    formData.append('advice_focus', adviceFocus)

    const url = type === 'csv'
      ? `${API_BASE}/upload/csv`
      : `${API_BASE}/upload/screenshot`

    try {
      const res = await fetch(url, { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Upload failed')
      const extra = data.analysis?.target ? ` Focus metric: ${data.analysis.target}.` : ''
      setStatus((data.message || 'Done.') + extra)
      setFile(null)
    } catch (err: any) {
      setStatus('Could not finish the upload: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-3xl mb-2">Upload</h1>
      <p className="text-[var(--muted)] mb-6">
        Spreadsheets do not need date/value/dimension mapping. Screenshots do not need a specific dashboard layout.
      </p>
      <div className="card">
        {projects.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Create a project on the home page first.</p>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="label">Project</label>
              <select className="field" value={selectedProject} onChange={e => setSelectedProject(e.target.value)}>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <UploadForm
              projectId={selectedProject}
              uploadType={type}
              setUploadType={setType}
              adviceFocus={adviceFocus}
              setAdviceFocus={setAdviceFocus}
              file={file}
              setFile={setFile}
              loading={loading}
              status={status}
              onSubmit={handleUpload}
            />
          </div>
        )}
      </div>
    </div>
  )
}
