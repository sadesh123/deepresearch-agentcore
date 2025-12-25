import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import './DxOView.css'

function DxOView({ result }) {
  const [activeStep, setActiveStep] = useState(0)

  if (!result) return null

  const { workflow } = result

  const stepIcons = {
    'Initial Research': '🔍',
    'Critical Review': '🔎',
    'Expert Validation': '👨‍🔬',
    'Final Synthesis': '📊'
  }

  return (
    <div className="dxo-view card">
      <div className="result-header">
        <h2>DxO Research Workflow Results</h2>
        <div className="question-display">
          <strong>Question:</strong> {result.question}
        </div>
      </div>

      <div className="workflow-timeline">
        {workflow.map((step, idx) => (
          <div
            key={idx}
            className={`timeline-step ${activeStep === idx ? 'active' : ''} ${idx < activeStep ? 'completed' : ''}`}
            onClick={() => setActiveStep(idx)}
          >
            <div className="step-marker">
              <div className="step-icon">{stepIcons[step.step] || '📝'}</div>
              <div className="step-number">{idx + 1}</div>
            </div>
            <div className="step-info">
              <div className="step-role">{step.role}</div>
              <div className="step-name">{step.step}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="workflow-content">
        {workflow[activeStep] && (
          <div className="step-detail">
            <div className="step-header">
              <span className="step-icon-large">
                {stepIcons[workflow[activeStep].step] || '📝'}
              </span>
              <div>
                <h3>{workflow[activeStep].role}</h3>
                <p className="step-subtitle">{workflow[activeStep].step}</p>
              </div>
            </div>

            <div className="step-content markdown-content">
              <ReactMarkdown>{workflow[activeStep].content}</ReactMarkdown>
            </div>

            <div className="step-navigation">
              <button
                className="nav-button"
                onClick={() => setActiveStep(Math.max(0, activeStep - 1))}
                disabled={activeStep === 0}
              >
                ← Previous Step
              </button>
              <button
                className="nav-button"
                onClick={() => setActiveStep(Math.min(workflow.length - 1, activeStep + 1))}
                disabled={activeStep === workflow.length - 1}
              >
                Next Step →
              </button>
            </div>
          </div>
        )}
      </div>

      {result.metadata && result.metadata.papers_found > 0 && (
        <div className="metadata-info">
          <strong>Research Sources:</strong> {result.metadata.papers_found} arXiv papers analyzed
        </div>
      )}
    </div>
  )
}

export default DxOView
