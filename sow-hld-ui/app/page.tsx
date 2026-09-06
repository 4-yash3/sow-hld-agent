"use client";

import React, { useState, useRef } from "react";
import { 
  Bot, Box, Code2, Download, Layers3, Loader2, 
  Maximize2, Menu, MessageSquareText, Moon, Network, 
  Paperclip, Send, Settings2, ShieldCheck, Smartphone, 
  Sparkles, Sun, X, Zap, ImageDown
} from "lucide-react";
import { useCopilot } from "@/lib/useCopilot";

const tabs = ["System Context HLD", "Sequence Diagram", "Data Entity Model"];
const Github = Code2;

function Node({ title, detail, icon: Icon = Box, accent = "", badge, online = false }: { title: string; detail: string; icon?: React.ElementType; accent?: string; badge?: string; online?: boolean }) {
  return (
    <div className={`architecture-node ${accent}`}>
      <div className="node-heading">
        <span className="node-icon"><Icon size={18} /></span>
        <span className="node-title">{title}</span>
        {badge && <span className="node-badge">{badge}</span>}
      </div>
      <p>{detail}</p>
      {online && <span className="node-online" aria-label="healthy" />}
    </div>
  );
}

function ArchitecturePreview() {
  return (
    <div className="architecture-preview" aria-label="System context architecture diagram">
      <div className="diagram-column clients">
        <span className="tier-label">EDGE TIER</span>
        <Node title="Web Client" detail="Next.js + SPA" icon={Layers3} online />
        <Node title="Mobile Native" detail="iOS / Android" icon={Smartphone} online />
      </div>
      <div className="diagram-column gateway">
        <span className="tier-label">GATEWAY TIER</span>
        <Node title="Kong API Gateway" detail="Token introspection, rate limiting & routing" icon={ShieldCheck} badge="INGRESS" accent="node-orange" />
        <span className="endpoint">/api/v2/core-banking</span>
      </div>
      <div className="diagram-column core">
        <span className="tier-label">CORE SERVICES</span>
        <Node title="Auth0 / OIDC IAM" detail="JWT verification & RBAC claims" icon={ShieldCheck} badge="OAuth2.1" />
        <Node title="Transaction Engine" detail="Account balances & double-entry ledger" icon={Zap} online />
        <Node title="Settlement Worker" detail="Kafka Sink" icon={Network} />
      </div>
      <div className="diagram-column state">
        <span className="tier-label">DATA & STATE</span>
        <Node title="PostgreSQL Aurora" detail="ACID compliant" icon={Box} badge="99.99%" />
        <Node title="Event Bus (Kafka)" detail="Audit logs & CDC" icon={Network} />
      </div>
      <span className="flow flow-one" />
      <span className="flow flow-two" />
      <span className="flow flow-three" />
      <span className="flow-vertical" />
    </div>
  );
}

export default function Dashboard() {
  const { 
    file, isUploading, messages, inputPrompt, setInputPrompt, 
    isSending, manifest, selectedDiagramKey, setSelectedDiagramKey, 
    viewMode, setViewMode, chatEndRef, handleFileUpload, sendMessage 
  } = useCopilot();

  const [imgError, setImgError] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [lightMode, setLightMode] = useState(false);
  const [zoom, setZoom] = useState(100);

  // Drag Panning State
  const canvasRef = useRef<HTMLDivElement>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0, scrollLeft: 0, scrollTop: 0 });

  const keys = Object.keys(manifest);
  const diagram = selectedDiagramKey ? manifest[selectedDiagramKey] : undefined;
  const previewUrl = typeof diagram?.preview_url === "string" ? diagram.preview_url : null;
  const sourcePath = typeof diagram?.image_path === "string" ? diagram.image_path : typeof diagram?.path === "string" ? diagram.path : "";
  const diagramSrc: string | null = previewUrl || (() => { 
    const filename = sourcePath.split(/[/\\]/).pop(); 
    return filename ? `http://localhost:8000/api/diagram-image/${filename}` : null; 
  })();

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 15, 250));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 15, 30));
  const handleZoomReset = () => {
    setZoom(100);
    if (canvasRef.current) {
      canvasRef.current.scrollLeft = 0;
      canvasRef.current.scrollTop = 0;
    }
  };

  // Mouse Drag Panning Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!canvasRef.current) return;
    setIsPanning(true);
    setPanStart({
      x: e.clientX,
      y: e.clientY,
      scrollLeft: canvasRef.current.scrollLeft,
      scrollTop: canvasRef.current.scrollTop
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning || !canvasRef.current) return;
    const dx = e.clientX - panStart.x;
    const dy = e.clientY - panStart.y;
    canvasRef.current.scrollLeft = panStart.scrollLeft - dx;
    canvasRef.current.scrollTop = panStart.scrollTop - dy;
  };

  const handleMouseUpOrLeave = () => {
    setIsPanning(false);
  };

  const handleDownloadImage = async () => {
    if (!diagramSrc) return;
    try {
      const response = await fetch(diagramSrc);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${selectedDiagramKey || "architecture_diagram"}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(diagramSrc, "_blank");
    }
  };

  return (
    <main className={`copilot-shell ${lightMode ? "light-mode" : ""}`}>
      {/* Header */}
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark"><Layers3 size={20} /></div>
          <span className="brand-name">SOW-to-HLD Interactive Copilot</span>
          <span className="live-badge">v2.4 · LIVE</span>
        </div>
        
        <div className="header-actions">
          <a href="http://localhost:8000/api/download/docx" className="header-button">
            <Download size={15} /> DOCX
          </a>
          <a href="http://localhost:8000/api/download/pptx" className="header-button header-button-warm">
            <Download size={15} /> PPTX Deck
          </a>
          <button className="icon-button" aria-label="Settings">
            <Settings2 size={18} />
          </button>
          
          <button 
            className="icon-button" 
            onClick={() => setLightMode(!lightMode)} 
            aria-label={lightMode ? "Switch to dark mode" : "Switch to light mode"}
            title={lightMode ? "Switch to dark mode" : "Switch to light mode"}
          >
            {lightMode ? <Moon size={18} /> : <Sun size={18} />}
          </button>

          <button className="avatar" aria-label="Profile">N</button>
          
          <button className="mobile-menu icon-button" onClick={() => setMenuOpen(!menuOpen)}>
            <Menu size={20} />
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <section className={`workspace ${menuOpen ? "menu-open" : ""}`}>
        <aside className="session-panel">
          <div className="panel-title">
            <span className="status-dot" /> HLD AGENT SESSION 
            <button onClick={() => setMenuOpen(false)} className="mobile-close"><X size={18} /></button>
            <button className="clear-button">Clear</button>
          </div>

          <div className="conversation">
            {messages.map((message, index) => (
              <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}>
                <span className="message-avatar">
                  {message.role === "assistant" ? <Bot size={17} /> : <MessageSquareText size={17} />}
                </span>
                <div className="message-bubble">
                  {message.content}
                  {index === 0 && (
                    <div className="suggestions">
                      <button onClick={() => setInputPrompt("Create a sequence diagram")}>+ Sequence Diagram</button>
                      <button onClick={() => setInputPrompt("Generate an ER diagram")}>+ ER Model</button>
                      <button onClick={() => setInputPrompt("Synthesize HLD")}>+ HLD</button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {file && (
              <div className="uploaded-file">
                <Box size={16} />
                <span>{file.name}</span>
                {isUploading ? <Loader2 className="spin" size={15} /> : <span className="file-ready">Parsed</span>}
              </div>
            )}

            {isSending && (
              <div className="agent-working">
                <Loader2 className="spin" size={16} /> Agent is mapping the architecture…
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="prompt-area">
            <input 
              type="file" 
              id="sow-file" 
              className="visually-hidden" 
              accept=".pdf" 
              onChange={(event) => event.target.files?.[0] && handleFileUpload(event.target.files[0])} 
            />
            <label htmlFor="sow-file" className="attach-button" title="Attach SOW PDF">
              <Paperclip size={18} />
            </label>
            <input 
              value={inputPrompt} 
              onChange={(event) => setInputPrompt(event.target.value)} 
              onKeyDown={(event) => event.key === "Enter" && sendMessage()} 
              placeholder="e.g. Generate an ER diagram or DFD..." 
            />
            <button className="send-button" onClick={sendMessage} disabled={isSending || !inputPrompt.trim()}>
              <Send size={18} />
            </button>
          </div>
        </aside>

        <section className="canvas-panel">
          <div className="canvas-toolbar">
            <nav className="diagram-tabs">
              {(keys.length ? keys.map(key => key.replace(/_/g, " ")) : tabs).map((name, index) => (
                <button 
                  key={name} 
                  onClick={() => { 
                    setActiveTab(index); 
                    if (keys[index]) { 
                      setSelectedDiagramKey(keys[index]); 
                      setImgError(false); 
                    } 
                  }} 
                  className={index === activeTab ? "active" : ""}
                >
                  {index === 0 && <Sparkles size={14} />} {name}
                </button>
              ))}
            </nav>

            <div className="canvas-actions">
              {/* Working Zoom Controls Group */}
              <div className="zoom-controls">
                <button className="zoom-btn" onClick={handleZoomOut} title="Zoom Out">−</button>
                <span className="zoom-text" onClick={handleZoomReset} title="Click to reset zoom">{zoom}%</span>
                <button className="zoom-btn" onClick={handleZoomIn} title="Zoom In">+</button>
              </div>

              {/* Download Diagram Button */}
              <button 
                className="icon-button" 
                onClick={handleDownloadImage} 
                title="Download current diagram image"
                disabled={!diagramSrc}
              >
                <ImageDown size={17} />
              </button>

              <button 
                onClick={() => setViewMode(viewMode === "diagram" ? "json" : "diagram")} 
                className={`view-toggle ${viewMode === "json" ? "selected" : ""}`}
                title="Toggle code view"
              >
                <Code2 size={17} />
              </button>
              
              <button className="icon-button" onClick={handleZoomReset} title="Fit diagram / Reset zoom">
                <Maximize2 size={17} />
              </button>
            </div>
          </div>

          {/* Canvas Viewport with Adaptive Zoom Origin & Drag Pan */}
          <div 
            className="canvas-content" 
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUpOrLeave}
            onMouseLeave={handleMouseUpOrLeave}
          >
            {keys.length > 0 && viewMode === "json" ? (
              <pre className="json-view">{JSON.stringify(diagram, null, 2)}</pre>
            ) : keys.length > 0 && diagramSrc && !imgError ? (
              <div 
                className={`canvas-viewport ${isPanning ? "panning" : "can-pan"}`}
                style={{
                  display: "flex",
                  justifyContent: zoom > 100 ? "flex-start" : "center",
                  alignItems: zoom > 100 ? "flex-start" : "center",
                  width: zoom > 100 ? `${zoom}%` : "100%",
                  height: zoom > 100 ? `${zoom}%` : "100%",
                }}
              >
                <div 
                  className="canvas-zoom-wrapper"
                  style={{ 
                    transform: `scale(${zoom / 100})`,
                    transformOrigin: zoom > 100 ? "0 0" : "center center"
                  }}
                >
                  <img 
                    className="generated-diagram" 
                    src={diagramSrc} 
                    alt={selectedDiagramKey} 
                    onError={() => setImgError(true)} 
                  />
                </div>
              </div>
            ) : (
              <div 
                className={`canvas-viewport ${isPanning ? "panning" : "can-pan"}`}
                style={{
                  display: "flex",
                  justifyContent: zoom > 100 ? "flex-start" : "center",
                  alignItems: zoom > 100 ? "flex-start" : "center",
                  width: zoom > 100 ? `${zoom}%` : "100%",
                  height: zoom > 100 ? `${zoom}%` : "100%",
                }}
              >
                <div 
                  className="canvas-zoom-wrapper"
                  style={{ 
                    transform: `scale(${zoom / 100})`,
                    transformOrigin: zoom > 100 ? "0 0" : "center center"
                  }}
                >
                  <ArchitecturePreview />
                </div>
              </div>
            )}
          </div>

          <footer className="canvas-footer">
            <span>Last rendered: <strong>just now</strong></span>
            <button><Github size={14} /> Edit Diagram</button>
          </footer>
        </section>
      </section>
    </main>
  );
}