import { useState } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CouncilView from './components/CouncilView'
import DxOView from './components/DxOView'
import { runCouncil, runDxO } from './api'

function App() {
  const [mode, setMode] = useState('council')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const handleSubmit = async (question) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      let data
      if (mode === 'council') {
        data = await runCouncil(question)
      } else {
        data = await runDxO(question)
      }
      setResult(data)
    } catch (err) {
      console.error('Error:', err)
      setError(err.response?.data?.detail || err.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Deep Research Agent</h1>
        <p className="subtitle">AI-Powered Research with LLM Council & DxO Framework</p>
      </header>

      <div className="container">
        <div className="mode-selector card">
          <h3>Select Research Mode</h3>
          <div className="mode-buttons">
            <button
              className={`mode-button ${mode === 'council' ? 'active' : ''}`}
              onClick={() => setMode('council')}
              disabled={loading}
            >
              <div className="mode-icon">⚖️</div>
              <div className="mode-title">LLM Council</div>
              <div className="mode-desc">3-stage democratic deliberation</div>
            </button>
            <button
              className={`mode-button ${mode === 'dxo' ? 'active' : ''}`}
              onClick={() => setMode('dxo')}
              disabled={loading}
            >
              <div className="mode-icon">🔬</div>
              <div className="mode-title">DxO Research</div>
              <div className="mode-desc">Sequential expert workflow</div>
            </button>
          </div>
        </div>

        <ChatInterface
          onSubmit={handleSubmit}
          loading={loading}
          mode={mode}
        />

        {error && (
          <div className="error card">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="loading card">
            <div className="spinner"></div>
            <p>
              {mode === 'council'
                ? 'Council members are deliberating...'
                : 'Research team is working...'}
            </p>
          </div>
        )}

        {result && !loading && (
          <div className="results">
            {mode === 'council' ? (
              <CouncilView result={result} />
            ) : (
              <DxOView result={result} />
            )}
          </div>
        )}
      </div>

      <footer className="app-footer">
        <p>Powered by AWS Bedrock AgentCore | Built for IHL Demo</p>
      </footer>
    </div>
  )
}

export default App
