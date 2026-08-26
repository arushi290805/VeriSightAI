'use client'

import { useState } from 'react'

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [type, setType] = useState('screenshot')
  const [status, setStatus] = useState('')

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    let url = 'http://localhost:8000/upload/screenshot'
    if (type === 'csv') {
      url = 'http://localhost:8000/upload/csv'
      formData.append('kpi_name', 'revenue')
      formData.append('grain', 'daily')
      formData.append('date_col', 'date')
      formData.append('value_col', 'value')
      formData.append('dimension_cols', 'region,product')
    }

    try {
      setStatus('Uploading...')
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setStatus('Success: ' + data.message)
    } catch (err: any) {
      setStatus('Error: ' + err.message)
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold mb-6">Upload Data</h1>
      <form onSubmit={handleUpload} className="space-y-4">
        <div>
          <label className="block mb-2 text-sm font-medium">Upload Type</label>
          <select 
            value={type} 
            onChange={e => setType(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-sm rounded-lg w-full p-2.5"
          >
            <option value="screenshot">Dashboard Screenshot (Gemini Vision)</option>
            <option value="csv">CSV File</option>
          </select>
        </div>
        
        <div className="flex items-center justify-center w-full">
          <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-slate-700 border-dashed rounded-lg cursor-pointer bg-slate-800 hover:bg-slate-700">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <p className="mb-2 text-sm text-slate-400">
                <span className="font-semibold">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-slate-500">{file ? file.name : (type === 'csv' ? 'CSV files only' : 'PNG/JPG only')}</p>
            </div>
            <input 
              type="file" 
              className="hidden" 
              accept={type === 'csv' ? '.csv' : '.png,.jpg,.jpeg'}
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>
        
        <button 
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 text-center"
        >
          Upload and Parse
        </button>
        
        {status && <div className="mt-4 p-4 bg-slate-800 rounded-lg text-sm">{status}</div>}
      </form>
    </div>
  )
}
