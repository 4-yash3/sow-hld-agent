// sow-hld-ui/lib/useCopilot.ts
import { useState, useRef, useEffect } from "react";

export interface Message {
  role: "assistant" | "user";
  content: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://sow-hld-agent.onrender.com";

export function useCopilot() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Upload your SOW PDF, then tell me what to build (e.g. 'Synthesize HLD', 'Create sequence diagram', 'Generate ER diagram').",
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [manifest, setManifest] = useState<Record<string, any>>({});
  const [selectedDiagramKey, setSelectedDiagramKey] = useState<string>("");
  const [viewMode, setViewMode] = useState<"diagram" | "json">("diagram");
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleFileUpload = async (uploadedFile: File) => {
    if (!uploadedFile) return;
    setFile(uploadedFile);
    setIsUploading(true);

    const formData = new FormData();
    formData.append("file", uploadedFile);
    formData.append("session_id", "default");

    try {
      const res = await fetch(`${BACKEND_URL}/api/upload-sow`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed with status: ${res.status}`);
      }

      await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `✅ Scope of Work document "${uploadedFile.name}" successfully parsed. Ready to design your architecture.`,
        },
      ]);
    } catch (err) {
      console.error("PDF upload error:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Error uploading PDF document. Please check the backend connection.",
        },
      ]);
    } finally {
      setIsUploading(false);
    }
  };

  const sendMessage = async () => {
    const text = inputPrompt.trim();
    if (!text || isSending) return;

    setInputPrompt("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsSending(true);

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: text, session_id: "default" }),
      });

      if (!res.ok) {
        throw new Error(`Chat failed with status: ${res.status}`);
      }

      const data = await res.json();

      if (data.reply) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.reply },
        ]);
      }

      if (data.manifest && Object.keys(data.manifest).length > 0) {
        setManifest(data.manifest);
        const keys = Object.keys(data.manifest);
        setSelectedDiagramKey(keys[keys.length - 1]);
      }
    } catch (err) {
      console.error("Agent chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Error communicating with the HLD Agent.",
        },
      ]);
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
    sendMessage,
  };
}