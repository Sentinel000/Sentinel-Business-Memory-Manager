import { create } from 'zustand';
import { ChatMessage } from '../types';
import { api } from '../lib/api';

interface ChatState {
  isDrawerOpen: boolean;
  conversationId: string | null;
  messages: ChatMessage[];
  isThinking: boolean;
  toggleDrawer: (open?: boolean) => void;
  sendMessage: (message: string) => Promise<void>;
  resetConversation: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  isDrawerOpen: false,
  conversationId: null,
  messages: [
    {
      id: 'welcome',
      sender: 'agent',
      content: "Hello! I'm Sentinel, your operational business memory. Ask me about active commitments, team blockers, or meeting transcripts.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ],
  isThinking: false,

  toggleDrawer: (open) => {
    set((state) => ({ isDrawerOpen: open ?? !state.isDrawerOpen }));
  },

  sendMessage: async (content) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    set((state) => ({
      messages: [...state.messages, userMsg],
      isThinking: true,
    }));

    try {
      const { conversationId } = get();
      const res = await api.post('/chat', {
        message: content,
        conversation_id: conversationId,
      });

      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        content: res.data.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tool_executions: res.data.tool_executions,
      };

      set((state) => ({
        messages: [...state.messages, agentMsg],
        conversationId: res.data.conversation_id,
        isThinking: false,
      }));
    } catch {
      set((state) => ({
        messages: [
          ...state.messages,
          {
            id: (Date.now() + 1).toString(),
            sender: 'agent',
            content: 'Sorry, I encountered an error processing your query. Please try again.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ],
        isThinking: false,
      }));
    }
  },

  resetConversation: () => {
    set({
      conversationId: null,
      messages: [
        {
          id: 'welcome',
          sender: 'agent',
          content: "Conversation cleared. What would you like to ask Sentinel?",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ],
    });
  },
}));
