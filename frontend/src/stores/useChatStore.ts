import { create } from 'zustand';
import { ChatMessage, Conversation } from '../types';
import { api, apiErrorMessage } from '../lib/api';

const stamp = () =>
  new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

interface ChatState {
  /** Threads belonging to the signed-in user, newest first. */
  conversations: Conversation[];
  conversationId: string | null;
  messages: ChatMessage[];
  isThinking: boolean;
  isLoadingThread: boolean;
  error: string | null;

  fetchConversations: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  newConversation: () => void;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  conversationId: null,
  messages: [],
  isThinking: false,
  isLoadingThread: false,
  error: null,

  fetchConversations: async () => {
    try {
      const res = await api.get('/conversations');
      set({ conversations: res.data ?? [] });
    } catch {
      // A failed thread list must not blank the composer — chat still works.
    }
  },

  /** Rehydrate a thread from the server, tool cards included. */
  selectConversation: async (id) => {
    if (get().conversationId === id) return;
    set({ isLoadingThread: true, error: null, conversationId: id, messages: [] });
    try {
      const res = await api.get(`/conversations/${id}`);
      const messages: ChatMessage[] = (res.data.messages ?? []).map(
        (m: { role: string; content: string; tool_executions?: ChatMessage['tool_executions'] }, i: number) => ({
          id: `${id}-${i}`,
          sender: m.role === 'user' ? 'user' : 'agent',
          content: m.content,
          timestamp: '',
          tool_executions: m.tool_executions ?? [],
        })
      );
      set({ messages, isLoadingThread: false });
    } catch (err) {
      set({
        isLoadingThread: false,
        error: apiErrorMessage(err, 'Could not load that conversation.'),
      });
    }
  },

  /** Start a fresh thread. The id is assigned by the server on first send. */
  newConversation: () => {
    set({ conversationId: null, messages: [], error: null, isThinking: false });
  },

  deleteConversation: async (id) => {
    try {
      await api.delete(`/conversations/${id}`);
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        ...(state.conversationId === id ? { conversationId: null, messages: [] } : {}),
      }));
    } catch (err) {
      set({ error: apiErrorMessage(err, 'Could not delete that conversation.') });
    }
  },

  sendMessage: async (content) => {
    const userMsg: ChatMessage = {
      id: `local-${Date.now()}`,
      sender: 'user',
      content,
      timestamp: stamp(),
    };
    set((state) => ({
      messages: [...state.messages, userMsg],
      isThinking: true,
      error: null,
    }));

    try {
      const res = await api.post('/chat', {
        message: content,
        conversation_id: get().conversationId,
      });

      // The API field is `reply`, not `response`.
      const agentMsg: ChatMessage = {
        id: `agent-${Date.now()}`,
        sender: 'agent',
        content: res.data.reply,
        timestamp: stamp(),
        tool_executions: res.data.tool_executions ?? [],
      };

      const isNewThread = get().conversationId === null;
      set((state) => ({
        messages: [...state.messages, agentMsg],
        conversationId: res.data.conversation_id,
        isThinking: false,
      }));

      // A brand-new thread needs to appear in the sidebar immediately.
      if (isNewThread) await get().fetchConversations();
    } catch (err) {
      set({
        isThinking: false,
        error: apiErrorMessage(err, 'Sentinel could not answer that. Please try again.'),
      });
    }
  },
}));
