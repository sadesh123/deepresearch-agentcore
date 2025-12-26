import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import './CouncilView.css'

function CouncilView({ result }) {
  const [activeStage, setActiveStage] = useState('stage1')
  const [activeTab, setActiveTab] = useState(0)

  console.log('CouncilView received result:', result)
  console.log('Result type:', typeof result)

  if (!result) return null

  // Parse result if it's a string
  let parsedResult = result
  if (typeof result === 'string') {
    console.log('Result is a string, parsing...')
    try {
      parsedResult = JSON.parse(result)
      console.log('Parsed result:', parsedResult)
    } catch (e) {
      console.error('Failed to parse result:', e)
      return <div className="error">Failed to parse response data</div>
    }
  }

  const { stage1, stage2, stage3, metadata } = parsedResult

  console.log('Destructured values:', { stage1, stage2, stage3, metadata, question: parsedResult.question })

  return (
    <div className="council-view card">
      <div className="result-header">
        <h2>Council Deliberation Results</h2>
        <div className="question-display">
          <strong>Question:</strong> {parsedResult.question}
        </div>
      </div>

      <div className="stage-selector">
        <button
          className={`stage-tab ${activeStage === 'stage1' ? 'active' : ''}`}
          onClick={() => setActiveStage('stage1')}
        >
          Stage 1: Responses
        </button>
        <button
          className={`stage-tab ${activeStage === 'stage2' ? 'active' : ''}`}
          onClick={() => setActiveStage('stage2')}
        >
          Stage 2: Rankings
        </button>
        <button
          className={`stage-tab ${activeStage === 'stage3' ? 'active' : ''}`}
          onClick={() => setActiveStage('stage3')}
        >
          Stage 3: Final Answer
        </button>
      </div>

      <div className="stage-content">
        {activeStage === 'stage1' && (
          <div className="stage1">
            <h3>Council Members' Responses</h3>
            <p className="stage-description">
              Each council member independently analyzed the question:
            </p>
            {stage1 && stage1.length > 0 ? (
              <>
                <div className="member-tabs">
                  {stage1.map((response, idx) => (
                    <button
                      key={idx}
                      className={`member-tab ${activeTab === idx ? 'active' : ''}`}
                      onClick={() => setActiveTab(idx)}
                    >
                      {response.member_id}
                    </button>
                  ))}
                </div>
                <div className="member-content">
                  {stage1[activeTab] && (
                    <div className="markdown-content">
                      <ReactMarkdown>{stage1[activeTab].content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p>No responses available.</p>
            )}
          </div>
        )}

        {activeStage === 'stage2' && (
          <div className="stage2">
            <h3>Peer Review & Rankings</h3>
            <p className="stage-description">
              Council members evaluated all responses anonymously:
            </p>

            {metadata && metadata.aggregate_rankings && metadata.aggregate_rankings.length > 0 && (
              <div className="aggregate-rankings">
                <h4>Aggregate Rankings</h4>
                <div className="ranking-list">
                  {metadata.aggregate_rankings.map((rank, idx) => (
                    <div key={idx} className="ranking-item">
                      <div className="rank-position">{idx + 1}</div>
                      <div className="rank-details">
                        <div className="rank-member">
                          <strong>{rank.member_id}</strong>
                        </div>
                        <div className="rank-stats">
                          Avg Position: {rank.average_position.toFixed(2)} |
                          Votes: {rank.vote_count}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stage2 && stage2.length > 0 && (
              <div className="rankings-detail">
                <h4>Individual Rankings</h4>
                <div className="member-tabs">
                  {stage2.map((ranking, idx) => (
                    <button
                      key={idx}
                      className={`member-tab ${activeTab === idx ? 'active' : ''}`}
                      onClick={() => setActiveTab(idx)}
                    >
                      {ranking.member_id}
                    </button>
                  ))}
                </div>
                <div className="ranking-content">
                  {stage2[activeTab] && (
                    <>
                      <div className="markdown-content">
                        <ReactMarkdown>{stage2[activeTab].raw_text}</ReactMarkdown>
                      </div>
                      <div className="extracted-ranking">
                        <strong>Extracted Ranking:</strong>{' '}
                        {stage2[activeTab].parsed_ranking && stage2[activeTab].parsed_ranking.join(' > ')}
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeStage === 'stage3' && (
          <div className="stage3">
            <h3>Chairman's Final Synthesis</h3>
            <p className="stage-description">
              The chairman synthesized all inputs into a comprehensive answer:
            </p>
            {stage3 && stage3.content ? (
              <div className="final-answer markdown-content">
                <ReactMarkdown>{stage3.content}</ReactMarkdown>
              </div>
            ) : (
              <p>No final synthesis available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default CouncilView
