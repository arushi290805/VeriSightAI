'use client'

import { FormEvent } from 'react'

type UploadFormProps = {
  projectId: string
  uploadType: string
  setUploadType: (v: string) => void
  adviceFocus: string
  setAdviceFocus: (v: string) => void
  file: File | null
  setFile: (f: File | null) => void
  loading: boolean
  status: string
  onSubmit: (e: FormEvent) => void
  compact?: boolean
}

export default function UploadForm({
  projectId,
  uploadType,
  setUploadType,
  adviceFocus,
  setAdviceFocus,
  file,
  setFile,
  loading,
  status,
  onSubmit,
  compact,
}: UploadFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {!compact && (
        <p className="text-sm text-[var(--muted)]">
          Project #{projectId}. You do not need to map columns. Tell us what you want advice on.
        </p>
      )}
      <div>
        <label className="label">File type</label>
        <select className="field" value={uploadType} onChange={e => setUploadType(e.target.value)}>
          <option value="csv">CSV spreadsheet</option>
          <option value="screenshot">Dashboard screenshot</option>
        </select>
      </div>
      <div>
        <label className="label">What should we advise on?</label>
        <input
          className="field"
          value={adviceFocus}
          onChange={e => setAdviceFocus(e.target.value)}
          placeholder={uploadType === 'csv' ? 'e.g. sales by city, or what drives quantity' : 'e.g. conversion, pipeline, or headcount cost'}
        />
      </div>
      <div>
        <label className="label">File</label>
        <input
          type="file"
          accept={uploadType === 'csv' ? '.csv' : '.png,.jpg,.jpeg,.webp'}
          onChange={e => setFile(e.target.files?.[0] || null)}
          className="text-sm"
        />
        {file && <p className="text-xs text-[var(--muted)] mt-1">{file.name}</p>}
      </div>
      <button type="submit" disabled={loading || !file} className="btn w-full">
        {loading ? 'Working through the file…' : 'Upload and analyze'}
      </button>
      {status && (
        <p className="text-sm leading-relaxed text-[var(--ink)] whitespace-pre-wrap">{status}</p>
      )}
    </form>
  )
}
