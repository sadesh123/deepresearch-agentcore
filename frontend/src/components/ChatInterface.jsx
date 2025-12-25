import { useState } from 'react'
import './ChatInterface.css'

function ChatInterface({ onSubmit, loading, mode }) {
  const [question, setQuestion] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (question.trim() && !loading) {
      onSubmit(question)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const placeholders = {
    council: 'Ask a research question for the council to deliberate... (e.g., "What are the key challenges in quantum computing?")',
    dxo: 'Enter a research topic for deep analysis... (e.g., "Latest advances in quantum error correction")'
  }

  return (
    <div className="chat-interface card">
      <form onSubmit={handleSubmit}>
        <div className="input-container">
          <textarea
            className="question-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholders[mode]}
            rows={3}
            disabled={loading}
          />
        </div>
        <div className="button-container">
          <button
            type="submit"
            className="button button-primary"
            disabled={loading || !question.trim()}
          >
            {loading ? 'Processing...' : `Start ${mode === 'council' ? 'Council' : 'DxO'} Research`}
          </button>
        </div>
        <div className="hint">
          Press Enter to submit, Shift+Enter for new line
        </div>
      </form>
    </div>
  )
}

export default ChatInterface
