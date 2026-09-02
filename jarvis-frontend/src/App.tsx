import { FormEvent, useEffect, useRef, useState } from "react";
import { sendChatMessage } from "./api/chat";
import { fetchVoices, requestSpeech, transcribeRecording, Voice } from "./api/speech";
import { AmbientHud } from "./components/AmbientHud";
import { ActivityMonitor } from "./components/ActivityMonitor";
import { ComponentState, SystemStatus } from "./components/SystemStatus";
import { BriefingPanel } from "./components/BriefingPanel";
import { MovablePanel } from "./components/MovablePanel";
import { OrbControl } from "./components/OrbControl";
import { waitForBackend } from "./api/system";
import { isWebActionRequest, planWebAction, WebAction } from "./webActions";
import { executeLocalAction, getLocalActionStatus, isLocalActionRequest, LocalAction, planLocalAction } from "./localActions";
import { DEMO_MODE } from "./config/mode";
import backgroundVideo from "./assets/Background_looping_for_web_inter…_202609011658.mp4";

type Message = { author: "user" | "jarvis"; text: string };
type Status = "idle" | "listening" | "thinking" | "speaking" | "error";
type PendingAction =
  | { type: "web"; action: WebAction }
  | { type: "local"; action: LocalAction };

function defaultPanelPositions() {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  return {
    activity: { x: 34, y: 118 },
    briefing: { x: 34, y: Math.max(490, viewportHeight - 268) },
    chat: { x: Math.max(360, viewportWidth - 404), y: Math.max(72, Math.round((viewportHeight - 540) / 2)) },
    orb: { x: Math.round((viewportWidth - 180) / 2), y: Math.round((viewportHeight - 180) / 2) },
    status: { x: 34, y: 292 },
  };
}

export function App() {
  const panelPositions = useRef(defaultPanelPositions());
  const sessionId = useRef(crypto.randomUUID());
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef(0);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState("en-US-GuyNeural");
  const [level, setLevel] = useState(0);
  const [backendState, setBackendState] = useState<ComponentState>("unknown");
  const [backendStarting, setBackendStarting] = useState(!DEMO_MODE);
  const [microphoneState, setMicrophoneState] = useState<ComponentState>("unknown");
  const [sttState, setSttState] = useState<ComponentState>("unknown");
  const [ttsState, setTtsState] = useState<ComponentState>("unknown");
  const [chatState, setChatState] = useState<ComponentState>("unknown");
  const [localActionsState, setLocalActionsState] = useState<ComponentState>("unknown");
  const [localActionsEnabled, setLocalActionsEnabled] = useState(false);
  const [networkState, setNetworkState] = useState<ComponentState>(() => (navigator.onLine ? "ready" : "error"));
  const [bluetoothState] = useState<ComponentState>(() => ("bluetooth" in navigator ? "ready" : "unknown"));
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (DEMO_MODE) {
        setBackendState("ready");
        setBackendStarting(false);
        setChatState("ready");
        setTtsState("ready");
        const items = await fetchVoices();
        if (!cancelled) {
          setVoices(items);
          setVoiceId(items[0]?.id ?? "demo-guy");
        }
        return;
      }

      const healthy = await waitForBackend();
      if (cancelled) return;
      setBackendState(healthy ? "ready" : "error");
      setBackendStarting(false);
      if (!healthy) {
        setError("Jarvis backend did not start. Restart the app and try again.");
        return;
      }
      setChatState("ready");
      const voiceRequest = fetchVoices();
      const localActionsRequest = getLocalActionStatus();
      try {
        const items = await voiceRequest;
        if (cancelled) return;
        setVoices(items);
        setTtsState("ready");
        if (!items.some((item) => item.id === voiceId)) setVoiceId(items[0]?.id ?? voiceId);
      } catch {
        if (!cancelled) setError("Voice options are unavailable. Text chat still works.");
      }
      try {
        const enabled = await localActionsRequest;
        if (cancelled) return;
        setLocalActionsEnabled(enabled);
        setLocalActionsState(enabled ? "ready" : "unknown");
      } catch {
        if (!cancelled) setLocalActionsState("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const updateNetwork = () => setNetworkState(navigator.onLine ? "ready" : "error");
    window.addEventListener("online", updateNetwork);
    window.addEventListener("offline", updateNetwork);
    return () => {
      window.removeEventListener("online", updateNetwork);
      window.removeEventListener("offline", updateNetwork);
    };
  }, []);

  useEffect(() => () => {
    stopSpeech();
    stopCapture();
  }, []);

  useEffect(() => {
    requestAnimationFrame(() => messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" }));
  }, [messages, status, pendingAction]);

  function stopSpeech() {
    if (DEMO_MODE && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    audioRef.current?.pause();
    audioRef.current = null;
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    audioUrlRef.current = null;
  }

  function stopCapture() {
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    animationRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    setLevel(0);
  }

  function speakWithBrowserSpeech(text: string) {
    if (!("speechSynthesis" in window)) {
      setStatus("idle");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onstart = () => {
      setTtsState("ready");
      setStatus("speaking");
    };
    utterance.onend = () => {
      setStatus("idle");
    };
    utterance.onerror = () => {
      setStatus("idle");
    };
    window.speechSynthesis.speak(utterance);
  }

  async function playSpeech(text: string) {
    if (DEMO_MODE) {
      speakWithBrowserSpeech(text);
      return;
    }
    try {
      stopSpeech();
      const url = URL.createObjectURL(await requestSpeech(text, voiceId));
      const audio = new Audio(url);
      audioRef.current = audio;
      audioUrlRef.current = url;
      audio.onended = () => {
        if (audioUrlRef.current === url) URL.revokeObjectURL(url);
        setStatus("idle");
      };
      await audio.play();
      setTtsState("ready");
      setStatus("speaking");
    } catch (reason) {
      setTtsState("error");
      setError(reason instanceof Error ? reason.message : "Speech generation is unavailable. The text reply is still available.");
      setStatus("idle");
    }
  }

  async function askJarvis(text: string) {
    stopSpeech();
    setError("");
    setPendingAction(null);
    setMessages((current) => [...current, { author: "user", text }]);

    if (DEMO_MODE) {
      if (isLocalActionRequest(text)) {
        const reply = "Local app actions will be connected to the backend on Day 2.";
        setMessages((current) => [...current, { author: "jarvis", text: reply }]);
        setStatus("idle");
        void playSpeech(reply);
        return;
      }
      if (isWebActionRequest(text)) {
        const reply = "Web actions will be connected to the backend on Day 2.";
        setMessages((current) => [...current, { author: "jarvis", text: reply }]);
        setStatus("idle");
        void playSpeech(reply);
        return;
      }
      setStatus("thinking");
      try {
        const result = await sendChatMessage(sessionId.current, text);
        setChatState("ready");
        setMessages((current) => [...current, { author: "jarvis", text: result.reply }]);
        void playSpeech(result.reply);
      } catch (reason) {
        setChatState("error");
        setError(reason instanceof Error ? reason.message : "Jarvis could not process that message.");
        setStatus("error");
      }
      return;
    }

    if (isLocalActionRequest(text)) {
      setStatus("thinking");
      try {
        const localAction = await planLocalAction(text);
        setPendingAction({ type: "local", action: localAction });
        setStatus("idle");
      } catch (reason) {
        setLocalActionsState("error");
        setError(reason instanceof Error ? reason.message : "Jarvis could not prepare that local application.");
        setStatus("error");
      }
      return;
    }

    if (isWebActionRequest(text)) {
      setStatus("thinking");
      try {
        const webAction = await planWebAction(text);
        setPendingAction({ type: "web", action: webAction });
        setStatus("idle");
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Jarvis could not prepare that web action.");
        setStatus("error");
      }
      return;
    }

    setStatus("thinking");
    try {
      const result = await sendChatMessage(sessionId.current, text);
      setChatState("ready");
      setMessages((current) => [...current, { author: "jarvis", text: result.reply }]);
      void playSpeech(result.reply);
    } catch (reason) {
      setChatState("error");
      setError(reason instanceof Error ? reason.message : "Jarvis could not process that message.");
      setStatus("error");
    }
  }

  async function confirmAction() {
    if (!pendingAction) return;
    const currentAction = pendingAction;
    setPendingAction(null);

    if (currentAction.type === "web") {
      window.open(currentAction.action.url, "_blank", "noopener,noreferrer");
      const reply = `Opening ${currentAction.action.label}.`;
      setMessages((current) => [...current, { author: "jarvis", text: reply }]);
      setStatus("idle");
      void playSpeech(reply);
      return;
    }

    if (currentAction.type === "local") {
      setStatus("thinking");
      try {
        const result = await executeLocalAction(currentAction.action.appId);
        setMessages((current) => [...current, { author: "jarvis", text: result.message }]);
        setLocalActionsState("ready");
        setStatus("idle");
        void playSpeech(result.message);
      } catch (reason) {
        setLocalActionsState("error");
        setError(reason instanceof Error ? reason.message : "Jarvis could not open that local application.");
        setStatus("error");
      }
    }
  }

  function cancelAction() {
    setPendingAction(null);
    const reply = "Action cancelled.";
    setMessages((current) => [...current, { author: "jarvis", text: reply }]);
    setStatus("idle");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || status === "thinking" || backendStarting) return;
    setInput("");
    await askJarvis(text);
  }

  async function startListening() {
    if (status === "thinking" || backendStarting || recorderRef.current) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("This browser does not support microphone recording. Text chat remains available.");
      return;
    }
    try {
      setError("");
      stopSpeech();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = stream;
      setMicrophoneState("ready");
      const context = new AudioContext();
      audioContextRef.current = context;
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const updateMeter = () => {
        analyser.getByteTimeDomainData(samples);
        const mean = samples.reduce((sum, sample) => sum + Math.abs(sample - 128), 0) / samples.length;
        setLevel(Math.min(1, mean / 26));
        animationRef.current = requestAnimationFrame(updateMeter);
      };
      updateMeter();
      const chunks: BlobPart[] = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = () => {
        recorderRef.current = null;
        const duration = performance.now() - recordingStartedAtRef.current;
        stopCapture();
        if (duration < 650) {
          setError("Recording was too short. Hold the button while speaking, then release.");
          setSttState("error");
          setStatus("error");
          return;
        }

        if (DEMO_MODE) {
          const demoNotice = "Voice transcription will be connected on Day 2.";
          setMessages((current) => [
            ...current,
            { author: "jarvis", text: demoNotice },
          ]);
          setSttState("ready");
          setStatus("idle");
          void playSpeech(demoNotice);
          return;
        }

        void (async () => {
          try {
            setStatus("thinking");
            const transcript = await transcribeRecording(new Blob(chunks, { type: "audio/webm" }));
            if (!transcript) throw new Error("No speech was detected. Please try again.");
            setSttState("ready");
            await askJarvis(transcript);
          } catch (reason) {
            setSttState("error");
            setError(reason instanceof Error ? reason.message : "Jarvis could not transcribe that recording.");
            setStatus("error");
          }
        })();
      };
      recorder.start();
      recordingStartedAtRef.current = performance.now();
      setStatus("listening");
    } catch (reason) {
      stopCapture();
      setMicrophoneState("error");
      setError(
        reason instanceof Error && reason.name === "NotAllowedError"
          ? "Microphone permission was denied. Text chat remains available."
          : "Jarvis could not access the microphone."
      );
      setStatus("error");
    }
  }

  function finishListening() {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }

  const active = status === "listening" || status === "thinking" || status === "speaking";
  const stateLabel = backendStarting
    ? "STARTING LOCAL BACKEND"
    : status === "listening"
    ? "LISTENING / HOLD TO TALK"
    : status === "thinking"
    ? "PROCESSING REQUEST"
    : status === "speaking"
    ? "VOICE OUTPUT ACTIVE"
    : "SYSTEM ONLINE";

  const statusItems = [
    { label: "BACKEND", state: backendState, detail: DEMO_MODE ? "DEMO MODE" : backendState === "ready" ? "ONLINE" : undefined },
    { label: "NETWORK", state: networkState, detail: networkState === "ready" ? "ONLINE" : "OFFLINE" },
    { label: "TEXT ENGINE", state: chatState },
    { label: "BLUETOOTH", state: bluetoothState, detail: bluetoothState === "ready" ? "AVAILABLE" : undefined },
    { label: "MICROPHONE", state: microphoneState },
    { label: "SPEECH TO TEXT", state: sttState },
    { label: "TEXT TO SPEECH", state: ttsState },
    { label: "LOCAL ACTIONS", state: localActionsState, detail: DEMO_MODE ? "DAY 2" : localActionsEnabled ? "READY" : "DISABLED" },
  ];

  return (
    <main className="app-shell">
      <video className="background-video" autoPlay muted loop playsInline preload="auto" aria-hidden="true">
        <source src={backgroundVideo} type="video/mp4" />
      </video>
      <AmbientHud active={active} level={status === "listening" ? level : status === "speaking" ? 0.72 : 0.35} />
      <MovablePanel id="orb" label="Jarvis voice orb" className="orb-panel" defaultPosition={panelPositions.current.orb}>
        <OrbControl
          disabled={status === "thinking" || backendStarting}
          state={status}
          onStart={() => void startListening()}
          onStop={finishListening}
        />
      </MovablePanel>
      <MovablePanel id="activity" label="Activity monitor" className="activity-panel" defaultPosition={panelPositions.current.activity}>
        <ActivityMonitor state={status} />
      </MovablePanel>
      <MovablePanel id="system-status" label="System status" className="status-panel" defaultPosition={panelPositions.current.status}>
        <SystemStatus items={statusItems} />
      </MovablePanel>
      <MovablePanel id="briefing" label="Local system briefing" className="briefing-panel-wrapper" defaultPosition={panelPositions.current.briefing}>
        <BriefingPanel />
      </MovablePanel>
      <MovablePanel id="conversation" label="Jarvis conversation" className="chat-panel" defaultPosition={panelPositions.current.chat}>
        <section className="chat-card" aria-label="Jarvis assistant">
          <p className="jarvis-brand">JARVIS</p>
          <h1>At your service.</h1>
          <p className="connection-state">{stateLabel}</p>
          <div className="messages" ref={messagesRef} aria-live="polite">
            {messages.length === 0 && !pendingAction && <p>Type a message or hold to talk.</p>}
            {messages.map((message, index) => (
              <p className={`message ${message.author}`} key={`${message.author}-${index}`}>
                {message.text}
              </p>
            ))}
            {status === "thinking" && <p className="message jarvis">Thinking…</p>}
            {pendingAction && (
              <div className="web-action-confirmation" role="alert">
                {pendingAction.type === "web" ? (
                  <>
                    <p>Open {pendingAction.action.label}?</p>
                    <small>{pendingAction.action.url}</small>
                  </>
                ) : (
                  <>
                    <p>Launch {pendingAction.action.label}?</p>
                    <small>Target: {pendingAction.action.appId}</small>
                  </>
                )}
                <div>
                  <button type="button" onClick={() => void confirmAction()}>
                    Confirm
                  </button>
                  <button type="button" onClick={cancelAction}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
          <button
            className={`talk-button ${status === "listening" ? "is-listening" : ""}`}
            type="button"
            onPointerDown={(event) => {
              event.currentTarget.setPointerCapture(event.pointerId);
              void startListening();
            }}
            onPointerUp={finishListening}
            onPointerCancel={finishListening}
            disabled={status === "thinking" || backendStarting}
          >
            {status === "listening" ? "Release to send" : backendStarting ? "Starting Jarvis…" : "Hold to talk"}
          </button>
          <form onSubmit={handleSubmit} noValidate className="composer">
            <label className="sr-only" htmlFor="chat-input">
              Message Jarvis
            </label>
            <input
              id="chat-input"
              value={input}
              maxLength={2000}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Type a message…"
              disabled={status === "thinking" || backendStarting}
            />
            <button type="submit" disabled={!input.trim() || status === "thinking" || backendStarting}>
              Send
            </button>
          </form>
          <label className="voice-picker" htmlFor="voice-select">
            Voice
            <select id="voice-select" value={voiceId} onChange={(event) => setVoiceId(event.target.value)} disabled={!voices.length}>
              {voices.map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.label}
                </option>
              ))}
            </select>
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </section>
      </MovablePanel>
    </main>
  );
}
