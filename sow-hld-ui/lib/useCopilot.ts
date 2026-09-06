// lib/useCopilot.ts
import { useState, useEffect, useRef } from "react";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export type DiagramManifest = Record<string, unknown>;

export function useCopilot() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Upload your SOW PDF, then tell me what to build (e.g. 'Synthesize HLD', 'Create sequence diagram', 'Generate ER diagram')."
    }
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [manifest, setManifest] = useState<Record<string, DiagramManifest>>({});
  const [selectedDiagramKey, setSelectedDiagramKey] = useState("");
  const [viewMode, setViewMode] = useState<"diagram" | "json">("diagram");

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleFileUpload = async (selectedFile: File) => {
    setFile(selectedFile);
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("${BACKEND_URL}/api/upload-sow", {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("Upload failed");

      setMessages(prev => [
        ...prev,
        { role: "assistant", content: `📁 **${selectedFile.name}** uploaded and parsed! What would you like to generate?` }
      ]);
    } catch {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "❌ Error uploading PDF document. Please check the backend." }
      ]);
    } finally {
      setIsUploading(false);
    }
  };

  const sendMessage = async () => {
    if (!inputPrompt.trim() || isSending) return;
    const userMsg = inputPrompt;
    setInputPrompt("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsSending(true);

    try {
      const res = await fetch("${BACKEND_URL}/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, session_id: "default" })
      });
      const data = await res.json();

      setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);

      if (data.manifest && Object.keys(data.manifest).length > 0) {
        setManifest(data.manifest);
        const keys = Object.keys(data.manifest);
        if (!selectedDiagramKey || !data.manifest[selectedDiagramKey]) {
          setSelectedDiagramKey(keys[0]);
        }
      }
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "❌ Error communicating with the agent." }]);
    } finally {
      setIsSending(false);
    }
  };

  return {
    file,
    isUploading,
    messages,
    inputPrompt,
    setInputPrompt,
    isSending,
    manifest,
    selectedDiagramKey,
    setSelectedDiagramKey,
    viewMode,
    setViewMode,
    chatEndRef,
    handleFileUpload,
    sendMessage
  };
}
