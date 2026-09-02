import { create } from 'zustand';
import { Meeting, MeetingDeletePreview } from '../types';
import { api, apiErrorMessage } from '../lib/api';

interface MeetingsState {
  meetings: Meeting[];
  currentMeeting: Meeting | null;
  isLoading: boolean;
  isProcessing: boolean;
  processingMessage: string;
  fetchMeetings: () => Promise<void>;
  fetchMeetingDetail: (id: string) => Promise<void>;
  uploadAudioMeeting: (file: File, title?: string) => Promise<Meeting>;
  createTextMeeting: (title: string, transcript: string) => Promise<Meeting>;
  previewDelete: (id: string) => Promise<MeetingDeletePreview>;
  deleteMeeting: (id: string) => Promise<number>;
}

export const useMeetingsStore = create<MeetingsState>((set, get) => ({
  meetings: [],
  currentMeeting: null,
  isLoading: false,
  isProcessing: false,
  processingMessage: '',

  fetchMeetings: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/meetings');
      set({ meetings: res.data, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  fetchMeetingDetail: async (id) => {
    set({ isLoading: true });
    try {
      const res = await api.get(`/meetings/${id}`);
      set({ currentMeeting: res.data, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  uploadAudioMeeting: async (file, title) => {
    set({ isProcessing: true, processingMessage: 'Transcribing speech with Qwen ASR Flash...' });
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    try {
      const res = await api.post('/meetings/audio', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      set({ isProcessing: false, processingMessage: '' });
      get().fetchMeetings();
      return res.data;
    } catch (err) {
      set({ isProcessing: false, processingMessage: '' });
      throw err;
    }
  },

  createTextMeeting: async (title, transcript) => {
    set({ isProcessing: true, processingMessage: 'Extracting action items with Sentinel AI...' });
    try {
      const res = await api.post('/meetings/text', { title, transcript });
      set({ isProcessing: false, processingMessage: '' });
      get().fetchMeetings();
      return res.data;
    } catch (err) {
      set({ isProcessing: false, processingMessage: '' });
      throw err;
    }
  },
  previewDelete: async (id) => {
    const res = await api.get(`/meetings/${id}/delete-preview`);
    return res.data as MeetingDeletePreview;
  },

  /** Permanent. Removes the meeting and every fact extracted from it. */
  deleteMeeting: async (id) => {
    try {
      const res = await api.delete(`/meetings/${id}`);
      set((state) => ({ meetings: state.meetings.filter((m) => m.id !== id) }));
      return (res.data?.facts_deleted as number) ?? 0;
    } catch (err) {
      // Surfaced, never swallowed: a failed knowledge delete means the meeting is
      // still there, and the founder needs to know it was not removed.
      throw new Error(apiErrorMessage(err, 'Could not delete that meeting.'));
    }
  },
}));
