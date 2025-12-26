import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CouncilView from './components/CouncilView'
import DxOView from './components/DxOView'
import Login from './components/Login'
import Callback from './components/Callback'
import { cyberarkAuth } from './services/cyberark-auth'
import { runCouncil, runDxO } from './api-gateway'

function App() {
  const [mode, setMode] = useState('council')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = () => {
      const authenticated = cyberarkAuth.isAuthenticated()
      setIsAuthenticated(authenticated)
      setIsCheckingAuth(false)
    }

    checkAuth()
  }, [])

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

  // Handle logout
  const handleLogout = () => {
    cyberarkAuth.logout()
    setIsAuthenticated(false)
    setResult(null)
  }

  // Show loading while checking auth
  if (isCheckingAuth) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh'
      }}>
        <div>Loading...</div>
      </div>
    )
  }

  // Handle OAuth callback
  if (window.location.pathname === '/callback') {
    return <Callback />
  }

  // Show login if not authenticated
  if (!isAuthenticated) {
    return <Login />
  }

  return (
    <div className="app">
      <header className="app-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h1>Deep Research Agent</h1>
            <p className="subtitle">AI-Powered Research with LLM Council & DxO Framework</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            {/* Authentication Status Badge */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              backgroundColor: '#d4edda',
              border: '1px solid #c3e6cb',
              borderRadius: '4px',
              fontSize: '14px'
            }}>
              <span style={{ color: '#155724', fontWeight: '500' }}>🔐 CyberArk Authenticated</span>
              <span style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                backgroundColor: '#28a745',
                borderRadius: '50%',
                animation: 'pulse 2s infinite'
              }}></span>
            </div>
            <button
              onClick={handleLogout}
              style={{
                padding: '8px 16px',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              Logout
            </button>
          </div>
        </div>
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
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
            <p style={{
              fontSize: '12px',
              color: '#6c757d',
              marginTop: '10px',
              fontStyle: 'italic'
            }}>
              🔐 Authenticated request via CyberArk → AgentCore Gateway
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
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          <p>Powered by AWS Bedrock AgentCore | Built for IHL Demo</p>
          <div style={{
            fontSize: '12px',
            color: '#666',
            padding: '5px 10px',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            border: '1px solid #dee2e6'
          }}>
            <strong>Auth Flow:</strong> CyberArk OAuth → AgentCore Gateway → Agent Runtime
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
