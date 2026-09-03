'use client';

import React, { useState, useRef } from 'react';
import { Mic, Square, Upload, FileText, Loader2 } from 'lucide-react';
import { useMeetingsStore } from '@/stores/useMeetingsStore';

export const AudioRecorderStudio: React.FC = () => {
  const { uploadAudioMeeting, createTextMeeting, isProcessing, processingMessage } = useMeetingsStore();
  const [activeTab, setActiveTab] = useState<'record' | 'upload' | 'text'>('record');
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [title, setTitle] = useState('');
  const [pastedText, setPastedText] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const file = new File([blob], `meeting-${Date.now()}.webm`, { type: 'audio/webm' });
        await uploadAudioMeeting(file, title || 'Live Browser Recording');
        setTitle('');
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordSeconds(0);
      timerRef.current = setInterval(() => setRecordSeconds((s) => s + 1), 1000);
    } catch {
      alert('Could not access microphone. Check browser permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await uploadAudioMeeting(file, title || file.name);
      setTitle('');
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pastedText.trim()) return;
    await createTextMeeting(title || 'Pasted Transcript Notes', pastedText.trim());
    setPastedText('');
    setTitle('');
  };

  return (
    <div className="stone-card p-6 space-y-6 bg-white">
      <div className="flex items-center justify-between border-b border-stone-border pb-4">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-ink-black">Meeting Intelligence Studio</h2>
          <p className="text-xs text-warm-gray">Record audio live or upload transcripts for Qwen ASR Flash processing</p>
        </div>

        {/* Tab Pills */}
        <div className="flex items-center gap-1 bg-stone-canvas p-1 rounded-full border border-stone-border text-xs">
          <button
            onClick={() => setActiveTab('record')}
            className={`px-3 py-1 rounded-full font-medium transition ${
              activeTab === 'record' ? 'bg-inverse text-white shadow-subtle' : 'text-warm-gray hover:text-ink-black'
            }`}
          >
            Live Record
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-3 py-1 rounded-full font-medium transition ${
              activeTab === 'upload' ? 'bg-inverse text-white shadow-subtle' : 'text-warm-gray hover:text-ink-black'
            }`}
          >
            Upload File
          </button>
          <button
            onClick={() => setActiveTab('text')}
            className={`px-3 py-1 rounded-full font-medium transition ${
              activeTab === 'text' ? 'bg-inverse text-white shadow-subtle' : 'text-warm-gray hover:text-ink-black'
            }`}
          >
            Paste Text
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Meeting Title (e.g., Weekly Product Sync)"
          className="w-full px-3.5 py-2 text-sm border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
        />

        {activeTab === 'record' && (
          <div className="p-8 bg-stone-canvas border border-dashed border-stone-border rounded-xl flex flex-col items-center justify-center space-y-4 text-center">
            {isRecording ? (
              <>
                <div className="w-16 h-16 rounded-full bg-rose-500 text-white flex items-center justify-center animate-pulse shadow-lg">
                  <Mic className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <span className="text-xl font-bold font-mono text-ink-black">
                    {Math.floor(recordSeconds / 60)}:{(recordSeconds % 60).toString().padStart(2, '0')}
                  </span>
                  <p className="text-xs text-rose-600 font-medium">Recording browser audio...</p>
                </div>
                <button onClick={stopRecording} className="btn-cyan bg-rose-600 hover:bg-rose-700 border-rose-700 text-xs px-6 py-2 flex items-center gap-2">
                  <Square className="w-4 h-4 fill-white" /> Stop & Process
                </button>
              </>
            ) : (
              <>
                <div className="w-14 h-14 rounded-full bg-sky-wash text-cyan-signal flex items-center justify-center">
                  <Mic className="w-6 h-6" />
                </div>
                <p className="text-xs text-warm-gray max-w-xs">
                  Click below to capture microphone audio directly via browser MediaRecorder.
                </p>
                <button onClick={startRecording} className="btn-cyan text-xs px-6 py-2.5 flex items-center gap-2">
                  <Mic className="w-4 h-4" /> Start Live Recording
                </button>
              </>
            )}
          </div>
        )}

        {activeTab === 'upload' && (
          <label className="p-8 bg-stone-canvas border border-dashed border-stone-border rounded-xl flex flex-col items-center justify-center space-y-3 cursor-pointer hover:border-cyan-signal transition">
            <Upload className="w-8 h-8 text-cyan-signal" />
            <span className="text-xs font-medium text-ink-black">Click to upload audio file</span>
            <span className="text-[11px] text-warm-gray">Supports .webm, .wav, .mp3, .m4a, .ogg, .flac</span>
            <input type="file" accept="audio/*" onChange={handleFileUpload} className="hidden" />
          </label>
        )}

        {activeTab === 'text' && (
          <form onSubmit={handleTextSubmit} className="space-y-3">
            <textarea
              rows={4}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste transcript turns or meeting notes here..."
              className="w-full p-3 text-xs border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
            />
            <button type="submit" disabled={!pastedText.trim() || isProcessing} className="btn-cyan text-xs px-5 py-2 flex items-center gap-1.5">
              <FileText className="w-4 h-4" /> Process Text Transcript
            </button>
          </form>
        )}
      </div>

      {isProcessing && (
        <div className="p-3 bg-sky-wash border border-cyan-edge/30 rounded-lg flex items-center gap-3 text-xs text-cyan-edge">
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span className="font-medium">{processingMessage}</span>
        </div>
      )}
    </div>
  );
};
