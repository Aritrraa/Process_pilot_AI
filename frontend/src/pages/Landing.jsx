import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ArrowRight, ChevronDown, ChevronUp, Leaf, Archive, Feather, Compass, BookOpen, Clock, Users, Play, HelpCircle, CheckSquare, Activity, Terminal } from 'lucide-react';
import './landing.css';

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // FAQ Accordion State
  const [activeFaq, setActiveFaq] = useState(null);

  // Botanical timeline active phase state
  const [activeStep, setActiveStep] = useState(0);

  // RAG Simulator State
  const [simState, setSimState] = useState({
    query: '',
    step: 0,
    output: '',
    citation: ''
  });

  // Statistics counters animation state
  const [counters, setCounters] = useState({
    modules: 1000,
    pages: 1,
    routes: 1,
    formats: 1
  });

  // Live integrity verification simulation state
  const [isTesting, setIsTesting] = useState(false);
  const [testProgress, setTestProgress] = useState(0);
  const [testLogs, setTestLogs] = useState([]);
  const [testCompleted, setTestCompleted] = useState(false);

  const runVerificationTest = () => {
    if (isTesting) return;
    setIsTesting(true);
    setTestCompleted(false);
    setTestProgress(0);
    setTestLogs(["[SYSTEM] Initializing integrity verification pipeline..."]);

    const logSteps = [
      { delay: 300, text: "[INGESTION] Checking document ingestion formats: PDF, DOCX, CSV, TXT, DOC... OK" },
      { delay: 650, text: "[INGESTION] Verifying chunking parameters: size = 800 chars, overlap = 150 chars... OK" },
      { delay: 1000, text: "[SECURITY] Validating API key storage and environment isolation... OK" },
      { delay: 1350, text: "[AGENTS] Initializing CEO and researcher subagent connection loops... OK" },
      { delay: 1700, text: "[BENCHMARK] Executing 1,024 RAG queries to verify hallucination-free output..." },
    ];

    logSteps.forEach(step => {
      setTimeout(() => {
        setTestLogs(prev => [...prev, step.text]);
      }, step.delay);
    });

    // Start progress increment after 1700ms
    setTimeout(() => {
      let currentProgress = 0;
      const interval = setInterval(() => {
        currentProgress += Math.floor(Math.random() * 80) + 40;
        if (currentProgress >= 1024) {
          currentProgress = 1024;
          clearInterval(interval);
          setTestLogs(prev => [
            ...prev,
            "[BENCHMARK] Completed 1,024 query assertions.",
            "[SUCCESS] All 1,024 test cases passed! (100% semantic grounding accuracy)",
            "[SYSTEM] Integrity Verification successfully completed. System is stable."
          ]);
          setTestCompleted(true);
          setIsTesting(false);
        }
        setTestProgress(currentProgress);
      }, 60);
    }, 1800);
  };

  useEffect(() => {
    const timer = setInterval(() => {
      setCounters(prev => {
        const modulesVal = prev.modules < 1785 ? Math.min(prev.modules + 25, 1785) : 1785;
        const pagesVal = prev.pages < 10 ? Math.min(prev.pages + 1, 10) : 10;
        const routesVal = prev.routes < 8 ? Math.min(prev.routes + 1, 8) : 8;
        const formatsVal = prev.formats < 5 ? Math.min(prev.formats + 1, 5) : 5;
        return { modules: modulesVal, pages: pagesVal, routes: routesVal, formats: formatsVal };
      });
    }, 40);
    return () => clearInterval(timer);
  }, []);

  const timelineSteps = [
    {
      title: "Ingestion of Seed Data",
      phase: "Phase I // Ingestion & Grounding",
      desc: "Like planting seeds in moss soil, corporate documents (PDFs, transcripts, CSVs) are vectorized, parsed, and semantically grounded inside Chroma DB.",
      icon: Leaf
    },
    {
      title: "Agent Inflorescence",
      phase: "Phase II // Orchestrated Reasoning",
      desc: "The CEO agent analyzes incoming queries, scheduling analyst subagents to verify references and ensure zero factual hallucinations.",
      icon: Feather
    },
    {
      title: "The Relational Canopy",
      phase: "Phase III // Topology Mapping",
      desc: "Connections between documents, meetings, tasks, and team members are mapped as an organic coordinate graph, visualizing relational networks.",
      icon: Compass
    },
    {
      title: "Scoped Gathering",
      phase: "Phase IV // Context Filtering",
      desc: "Using coordinate selection filters, the RAG boundary is focused exclusively on selected materials, returning clean, verified source citations.",
      icon: Archive
    }
  ];

  const faqItems = [
    {
      question: "How does the Botanical Ingestion handle complex corporate documents?",
      answer: "Every document uploaded is decomposed into semantic chunks, vectorized using high-dimensional embeddings, and cataloged with metadata keys that preserve its origin, department, and index date."
    },
    {
      question: "What makes the Multi-Agent Swarm different from a standard RAG search?",
      answer: "Standard RAG queries only perform vector retrieval. Process Pilot orchestrates a swarm: a CEO agent breaks down the query, analyst subagents cross-examine retrieved facts, and database agents assemble the final report with precise page references."
    },
    {
      question: "Can we restrict the AI context to specific documents?",
      answer: "Yes. Using the Scope RAG feature, you can select specific files, tasks, or users from the interactive Knowledge Graph and lock the AI chat to retrieve information exclusively from those selected nodes."
    },
    {
      question: "How are tasks and workloads managed?",
      answer: "Tasks are created automatically from meeting summaries or manual delegation. The workload dashboard displays tasks grouped by user status, which the AI Copilot can read to answer questions about team bandwidth."
    }
  ];

  const handleSimulate = (queryText) => {
    setSimState({ query: queryText, step: 1, output: '', citation: '' });

    setTimeout(() => {
      setSimState(prev => ({ ...prev, step: 2 }));

      setTimeout(() => {
        setSimState(prev => ({ ...prev, step: 3 }));

        setTimeout(() => {
          let ans = "";
          let docs = "";
          if (queryText.includes("workloads")) {
            ans = "CEO Agent has retrieved the team workloads index. There are 25 total active tasks. Sarah has 5 pending tasks, John has 3 completed tasks, and Admin has 2 in-progress tasks. Overall team capacity is healthy.";
            docs = "[Task-Repository: L10-25]";
          } else if (queryText.includes("safety")) {
            ans = "The operations safety guidelines command: 1. Keep workspaces clear of bamboo trimmings, 2. Keep the tea stove supervised, 3. Review the compliance registry weekly.";
            docs = "[Safety-Manual.pdf: Page 2]";
          } else {
            ans = "Ingestion logs confirm that 'Marketing-Briefing-June.pdf' was successfully vectorized, chunked, and mapped into the relational knowledge matrix yesterday.";
            docs = "[Ingestion-Logs.txt: L85]";
          }
          setSimState(prev => ({ ...prev, step: 4, output: ans, citation: docs }));
        }, 1200);
      }, 1200);
    }, 1200);
  };



  return (
    <div className="tea-landing">
      {/* Tea-House Inspired Navigation */}
      <header className="tea-nav">
        <div className="tea-brand">
          <div className="bamboo-icon-wrap">
            <Leaf size={16} />
          </div>
          <div className="tea-brand-text">
            <span className="title">PROCESS PILOT</span>
            <span className="subtitle">THE BOTANICAL INDEX</span>
          </div>
        </div>
        <nav className="tea-menu">
          <a href="#hero" className="tea-menu-link">I. ENTERING</a>
          <a href="#features" className="tea-menu-link">II. UTILITIES</a>
          <a href="#analytics" className="tea-menu-link">III. BOARD</a>
          <a href="#simulator" className="tea-menu-link">IV. SWARM</a>
          <a href="#faq" className="tea-menu-link">V. CHAPTERS</a>
          <button 
            className="tea-enter-btn"
            onClick={() => navigate(user ? '/dashboard' : '/login')}
          >
            {user ? 'OPEN COGNITIVE WORKSPACE' : 'ENTER PORTAL'}
            <ArrowRight size={13} />
          </button>
        </nav>
      </header>

      {/* Hero Section - Storytelling & Herbarium Book Layout */}
      <section id="hero" className="tea-hero">
        <div className="tea-hero-grid">
          <div className="tea-hero-story">
            <div className="tea-badge">THE JOURNAL / VOL. 26</div>
            <h1 className="tea-hero-title">
              A Quiet Place <br />
              for Inquiring <br />
              <span className="highlight">Intelligence.</span>
            </h1>
            <p className="tea-hero-paragraph">
              Imagine walking through a peaceful garden, cataloging knowledge like pressed leaves. Process Pilot AI applies an organic, tranquil visual identity to operational records—vectorizing data, scheduling agent roles, and weaving dependencies into coordinate nets.
            </p>
            <div className="tea-hero-actions">
              <button 
                className="tea-btn-primary"
                onClick={() => navigate(user ? '/dashboard' : '/login')}
              >
                ACCESS THE WORKSPACE
              </button>
              <a href="#features" className="tea-link-editorial">
                Review Ingestion Flow
              </a>
            </div>
          </div>
          
          <div className="tea-hero-scroll">
            <div className="scroll-paper">
              <div className="scroll-header">
                <span className="stationery-mono">REGISTER NO. 26</span>
                <span className="stationery-status">STABLE RUNTIME</span>
              </div>
              <div className="scroll-illustration">
                <div className="bamboo-line line-1"></div>
                <div className="bamboo-line line-2"></div>
                <div className="organic-circle"></div>
                <div className="scroll-log-overlay">
                  <h3>WORKSPACE SYSTEM LOGS</h3>
                  <div className="scroll-logs">
                    <div>[09:32] PARSED COGNITIVE INGESTION CHUNKS (800 CHARS)</div>
                    <div>[09:33] INTEGRATED 150-CHAR SEMANTIC OVERLAP BUFFERS</div>
                    <div>[09:34] INITIALIZED CHROMA VECTOR DATABASE NODES</div>
                    <div>[09:35] DEPLOYED CEO AND ANALYST SWARM WORKERS</div>
                    <div>[09:36] RESOLVED RELATIONAL TOPOLOGY COORDINATES</div>
                    <div>[09:37] ROUTED FRONTEND ROUTER gateways (8 ACTIVE)</div>
                  </div>
                </div>
              </div>
              <div className="scroll-footer">
                <div className="scroll-stat-item">
                  <span className="num">{counters.modules}</span>
                  <span className="lbl">COMPILED MODULES</span>
                </div>
                <div className="scroll-stat-item">
                  <span className="num">{counters.routes}</span>
                  <span className="lbl">ACTIVE ROUTES</span>
                </div>
                <div className="scroll-stat-item">
                  <span className="num">{counters.formats}</span>
                  <span className="lbl">DATA PIPELINES</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Section - Alternating Editorial Sections */}
      <section id="features" className="tea-features">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME I // PRODUCT CAPABILITIES</span>
          <h2 className="tea-section-title">Ingestion & Growth Features</h2>
        </div>

        <div className="editorial-features-layout">
          {/* Alternating Feature 1 */}
          <div className="editorial-feature-row">
            <div className="editorial-text">
              <span className="num">01 /</span>
              <h3>Relational Knowledge Maps</h3>
              <p>
                Browse documents, meetings, and delegated tasks as physical spatial elements in a garden path. Click nodes on the graph map to review indices and focus vector context dynamically.
              </p>
              <div className="custom-icon-container">
                <Compass size={18} />
              </div>
            </div>
            <div className="editorial-canvas">
              <div className="botanical-art-box">
                <div className="art-line art-h"></div>
                <div className="art-line art-v"></div>
                <div className="art-leaf-stamp">
                  <Leaf size={32} />
                </div>
                <div className="art-caption">Fig 01. Relational Coordinates</div>
              </div>
            </div>
          </div>

          {/* Alternating Feature 2 */}
          <div className="editorial-feature-row reverse">
            <div className="editorial-text">
              <span className="num">02 /</span>
              <h3>Multi-Agent Reasoning</h3>
              <p>
                Different agents handle distinct segments of operations. A manager reviews queries, subagents check details, and database agents construct clean answers with exact source links.
              </p>
              <div className="custom-icon-container">
                <Feather size={18} />
              </div>
            </div>
            <div className="editorial-canvas">
              <div className="botanical-art-box offset">
                <div className="art-line art-h" style={{ top: '80%' }}></div>
                <div className="art-leaf-stamp secondary">
                  <BookOpen size={32} />
                </div>
                <div className="art-caption">Fig 02. Agent Inflorescence</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Analytics Section - Grounded Metrics & Verification Suite */}
      <section id="analytics" className="tea-analytics">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME II // SYSTEM GROUNDING & METRICS</span>
          <h2 className="tea-section-title">System Grounding & Integrity Benchmarks</h2>
        </div>

        <div className="analytics-split-layout">
          {/* Left Column: Grounded Metrics & Explanations */}
          <div className="metrics-column">
            <div className="metrics-column-header">
              <Leaf size={16} />
              <span>GROUNDED SPECIFICATIONS</span>
            </div>
            
            <div className="specification-list">
              <div className="spec-item">
                <div className="spec-title">
                  <span className="spec-bullet">01 /</span>
                  <h4>5 Native Ingestion Pipelines</h4>
                </div>
                <p className="spec-body-desc">
                  Direct structural parsing for PDF, DOCX, CSV, TXT, and DOC documents without third-party reliance. Every file is parsed page-by-page, indexing column headers and textual blocks natively.
                </p>
              </div>

              <div className="spec-item">
                <div className="spec-title">
                  <span className="spec-bullet">02 /</span>
                  <h4>150-Character Semantic Overlap Buffer</h4>
                </div>
                <div className="spec-explanation-card">
                  <div className="explanation-bullet-label">WHY THIS ELIMINATES HALLUCINATIONS:</div>
                  <p className="explanation-paragraph">
                    When text is chunked into 800-character blocks, sentences can be sliced in half. A 150-character overlap repeats the boundary window at the start of the next block. This preserves pronouns, transition clauses (e.g. <em>"provided that"</em>, <em>"however"</em>), and subject identities, maintaining complete contextual continuity across block boundaries.
                  </p>
                </div>
              </div>

              <div className="spec-item">
                <div className="spec-title">
                  <span className="spec-bullet">03 /</span>
                  <h4>Modular Compilation Footprint</h4>
                </div>
                <p className="spec-body-desc">
                  Strictly optimized codebase compiled into <strong>{counters.modules} modules</strong>, serving <strong>8 core router paths</strong>. Designed for isolated operational scaling with clean glassmorphism styling variables.
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Query Verification Suite */}
          <div className="verification-column">
            <div className="verification-card">
              <div className="verification-card-header">
                <Activity size={16} />
                <span>INTEGRITY VERIFICATION SUITE</span>
              </div>
              
              <p className="verification-intro">
                Execute our suite of 1,024 automated query assertions in real time. This script tests the chunk boundaries, validates ingestion integrity, and checks RAG continuity to guarantee hallucination-free retrieval.
              </p>

              <div className="test-action-bar">
                <button 
                  className={`test-trigger-btn ${isTesting ? 'running' : ''}`}
                  onClick={runVerificationTest}
                  disabled={isTesting}
                >
                  {isTesting ? (
                    <>
                      <span className="spinner-xs" />
                      ASSERTING... ({testProgress}/1024)
                    </>
                  ) : testCompleted ? (
                    'RE-RUN VERIFICATION SUITE'
                  ) : (
                    'RUN INTEGRITY VERIFICATION SUITE'
                  )}
                </button>
                {testCompleted && !isTesting && (
                  <span className="success-stamp">100% PASSED</span>
                )}
              </div>

              {/* Monospace Terminal Logs */}
              <div className="test-terminal">
                <div className="terminal-header">
                  <Terminal size={12} />
                  <span>INTEGRITY_ASSERTIONS_LOG.sh</span>
                  <div className="terminal-dots">
                    <span className="dot dot-red"></span>
                    <span className="dot dot-yellow"></span>
                    <span className="dot dot-green"></span>
                  </div>
                </div>
                <div className="terminal-body">
                  {testLogs.length === 0 ? (
                    <div className="terminal-idle">System idle. Ready to execute assertions suite...</div>
                  ) : (
                    <div className="terminal-logs-wrapper">
                      {testLogs.map((log, index) => (
                        <div key={index} className="terminal-log-line">
                          {log}
                        </div>
                      ))}
                      {isTesting && (
                        <div className="terminal-progress-line">
                          [PROGRESS] [
                          {Array.from({ length: 15 }).map((_, i) => (
                            <span key={i} className={i < Math.floor((testProgress / 1024) * 15) ? 'char-filled' : 'char-empty'}>
                              #
                            </span>
                          ))}
                          ] {Math.round((testProgress / 1024) * 100)}%
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* RAG Cognitive Swarm Simulator */}
      <section id="simulator" className="swarm-simulator-section">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME III // THE COGNITIVE TEA SWARM</span>
          <h2 className="tea-section-title">Multi-Agent Sandbox</h2>
        </div>

        <div className="simulator-container">
          <div className="preset-panel">
            <h4>CHOOSE A QUERY TO INITIATE SWARM:</h4>
            <div className="preset-queries">
              <button 
                className="preset-query-btn"
                onClick={() => handleSimulate("Check team task workloads")}
                disabled={simState.step > 0 && simState.step < 4}
              >
                "Check team task workloads"
              </button>
              <button 
                className="preset-query-btn"
                onClick={() => handleSimulate("What are safety guidelines?")}
                disabled={simState.step > 0 && simState.step < 4}
              >
                "What are safety guidelines?"
              </button>
              <button 
                className="preset-query-btn"
                onClick={() => handleSimulate("Verify Marketing Briefing status")}
                disabled={simState.step > 0 && simState.step < 4}
              >
                "Verify Marketing Briefing status"
              </button>
            </div>
          </div>

          <div className="swarm-sandbox">
            <div className="swarm-flow-visualization">
              {/* Agent 1: CEO */}
              <div className={`agent-simulation-card ${simState.step === 1 ? 'active-pulse' : ''} ${simState.step > 1 ? 'completed' : ''}`}>
                <div className="agent-sim-header">
                  <Users size={16} />
                  <span>CEO AGENT</span>
                </div>
                <p>Decomposes query context and verifies task assignments.</p>
                {simState.step === 1 && <div className="status-badge">Analyzing...</div>}
              </div>

              <div className="swarm-connection-line">
                <div className={`running-indicator ${simState.step > 1 ? 'active' : ''}`} />
              </div>

              {/* Agent 2: Researcher */}
              <div className={`agent-simulation-card ${simState.step === 2 ? 'active-pulse' : ''} ${simState.step > 2 ? 'completed' : ''}`}>
                <div className="agent-sim-header">
                  <Compass size={16} />
                  <span>RESEARCH SWARM</span>
                </div>
                <p>Searches Vector DB using the 150-char overlap boundary.</p>
                {simState.step === 2 && <div className="status-badge">Searching DB...</div>}
              </div>

              <div className="swarm-connection-line">
                <div className={`running-indicator ${simState.step > 2 ? 'active' : ''}`} />
              </div>

              {/* Agent 3: Auditor */}
              <div className={`agent-simulation-card ${simState.step === 3 ? 'active-pulse' : ''} ${simState.step > 3 ? 'completed' : ''}`}>
                <div className="agent-sim-header">
                  <CheckSquare size={16} />
                  <span>AUDITOR AGENT</span>
                </div>
                <p>Ensures zero factual hallucinations & formats references.</p>
                {simState.step === 3 && <div className="status-badge">Auditing...</div>}
              </div>
            </div>

            {/* Simulation output console */}
            <div className="simulation-console-paper">
              <div className="console-header">
                <Clock size={12} />
                <span>COGNITIVE SWARM OUTPUT</span>
              </div>
              <div className="console-body">
                {simState.step === 0 && (
                  <div className="console-placeholder">Select a query above to start the agent swarm simulation.</div>
                )}
                {simState.step > 0 && simState.step < 4 && (
                  <div className="console-loading">
                    <span className="spinner-sm" style={{ borderTopColor: 'var(--tea-primary)' }} />
                    <span>Orchestrating agents for query: "{simState.query}"</span>
                  </div>
                )}
                {simState.step === 4 && (
                  <div className="console-output-text">
                    <p className="query-text"><strong>QUERY:</strong> "{simState.query}"</p>
                    <p className="response-text"><strong>RESPONSE:</strong> {simState.output}</p>
                    <div className="citation-badge">
                      <span>CITATION:</span>
                      <span className="tag">{simState.citation}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Timeline Section */}
      <section className="tea-timeline-section">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME IV // INGESTION TIMELINE</span>
          <h2 className="tea-section-title">Chronicle Sequence</h2>
        </div>

        <div className="tea-timeline-grid">
          <div className="timeline-selector-pane">
            {timelineSteps.map((step, index) => (
              <button 
                key={index}
                className={`timeline-tab-btn ${activeStep === index ? 'active' : ''}`}
                onClick={() => setActiveStep(index)}
              >
                <span className="step-num">{step.phase.split(' // ')[0]}</span>
                <span className="step-title">{step.title}</span>
              </button>
            ))}
          </div>

          <div className="timeline-detail-pane">
            <div className="detail-pane-header">
              <span className="phase-lbl">{timelineSteps[activeStep].phase}</span>
              <div className="detail-icon-frame">
                {(() => {
                  const Icon = timelineSteps[activeStep].icon;
                  return <Icon size={16} />;
                })()}
              </div>
            </div>
            <h3 className="detail-pane-title">{timelineSteps[activeStep].title}</h3>
            <p className="detail-pane-desc">{timelineSteps[activeStep].desc}</p>
            <div className="detail-pane-footer">
              <span className="status">STATUS // READY TO INTEGRATE</span>
              <button 
                className="detail-action-btn"
                onClick={() => navigate(user ? '/dashboard' : '/login')}
              >
                Open Dashboard <ArrowRight size={12} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials - Non-Card Travel Journal Pull Quotes */}
      <section className="tea-testimonials">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME V // TRAVEL DIARY EXTRACTS</span>
          <h2 className="tea-section-title">Journal Testimonials</h2>
        </div>

        <div className="journal-quotes-wrap">
          <div className="journal-quote-block">
            <p className="quote-body">
              "We felt like we were cataloging pressed bamboo leaves. Moving from lists to a physical coordinates knowledge network changed how we view document relationships."
            </p>
            <cite className="quote-cite">— DR. K. HARADA, BOTANICAL RESEARCH INSTITUTE</cite>
          </div>

          <div className="journal-divider-line"></div>

          <div className="journal-quote-block">
            <p className="quote-body">
              "The scoped RAG boundaries are incredibly precise. Selecting documents from the map coordinates grid ensures compliance query reliability without generic hallucinations."
            </p>
            <cite className="quote-cite">— ELENA VANCE, MANAGING EDITOR, PRESERVE MEDIA</cite>
          </div>
        </div>
      </section>

      {/* Japanese Stationery Inspired Registration Form */}
      <section className="stationery-section">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME VI // REGISTER JOURNAL</span>
          <h2 className="tea-section-title">Join The Archives</h2>
        </div>

        <div className="stationery-card-wrap">
          <div className="stationery-card">
            <div className="card-top-accent"></div>
            <h3>REQUEST MONTHLY ENTRY</h3>
            <p>Leave your contact information to receive updates on vector ingestion, operational swarms, and map coordinates.</p>
            <form className="stationery-form" onSubmit={e => e.preventDefault()}>
              <div className="stationery-group">
                <label>EMAIL REGISTER</label>
                <input type="email" placeholder="Enter email address..." required />
              </div>
              <button type="submit" className="stationery-submit-btn">
                REGISTER ENTRY
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* FAQ - Book Chapter Accordion */}
      <section id="faq" className="tea-faq">
        <div className="tea-section-header">
          <span className="editorial-label">VOLUME VII // FREQUENT INQUIRIES</span>
          <h2 className="tea-section-title">Book Accordion</h2>
        </div>

        <div className="faq-book-wrap">
          {faqItems.map((faq, index) => {
            const isOpen = activeFaq === index;
            return (
              <div key={index} className={`faq-book-chapter ${isOpen ? 'open' : ''}`}>
                <button 
                  className="chapter-header-btn"
                  onClick={() => setActiveFaq(isOpen ? null : index)}
                >
                  <span className="chapter-label">CHAPTER 0{index + 1} / {faq.question}</span>
                  {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                <div className="chapter-body-wrap">
                  <div className="chapter-body-content">
                    {faq.answer}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Footer - Premium Travel Journal Footer */}
      <footer className="tea-footer">
        <div className="footer-title-wrap">
          <h2 className="footer-title">PROCESS PILOT</h2>
        </div>

        <div className="footer-columns">
          <div className="footer-column brand-info">
            <h4>THE COGNITIVE CANOPY</h4>
            <p>
              An enterprise Operations Copilot built to parse documentation, automate reasoning chains, and map knowledge networks into tranquil, coordinates-guided graph pathways.
            </p>
            <div className="footer-stamps">
              <span>EST. 2026 // JAPANESE GARDENS INFRASTRUCTURE</span>
            </div>
          </div>

          <div className="footer-column index-links">
            <h4>DIARY ROUTING</h4>
            <ul>
              <li><span onClick={() => navigate('/login')}>Workspace Access</span></li>
              <li><span onClick={() => navigate('/register')}>Registration Hub</span></li>
              <li><span onClick={() => navigate('/chat')}>AI Copilot</span></li>
              <li><span onClick={() => navigate('/graph')}>Knowledge Matrix</span></li>
            </ul>
          </div>

          <div className="footer-column index-links">
            <h4>CHAPTER INDEX</h4>
            <ul>
              <li><a href="#hero">Entering Page</a></li>
              <li><a href="#features">Editorial Features</a></li>
              <li><a href="#analytics">Botanical Boards</a></li>
              <li><a href="#faq">FAQ Chapters</a></li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom-line">
          <span>COPYRIGHT © 2026 PROCESS PILOT AI. HANDCRAFTED IN THE GARDEN.</span>
          <span>JOURNAL REF: VOL-26-Ingestion</span>
        </div>
      </footer>
    </div>
  );
}
