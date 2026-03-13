import { AxiosInstance } from 'axios';
import createHttpClient from '@/utils/createHttpClient';

/**
 * Multi-turn Chat Service
 * Xử lý communication với multi-turn conversation API
 */

export interface ChatSession {
    session_id: string;
    session_name: string;
    created_at: string;
    message_count: number;
    total_tokens: number;
    last_message_at: string;
}

export interface ChatMessage {
    message_id?: number;
    turn_number: number;
    user_query: string;
    ai_response: string;
    citations: CitationModel[];
    tokens_used?: {
        query_tokens: number;
        response_tokens: number;
        total_tokens: number;
    };
    api_response_time_ms?: number;
    created_at?: string;
}

export interface CitationModel {
    mapc: string;
    noidung: string;
    ten: string;
    _link?: string;
    chude_id?: string;
    demuc_id?: string;
}

export interface ChatResponse {
    status: string;
    data?: any;
    message?: string;
    error?: string;
}

export interface ConversationMemory {
    id: number;
    version: number;
    summary: string;
    key_topics: string[];
    important_facts: string[];
    is_context_summarized: boolean;
    truncated_from_turn?: number;
}

export interface SecurityLog {
    id: number;
    action: string;
    status: string;
    ip_address?: string;
    details?: string;
    timestamp: string;
}

class ChatService {
    private client: AxiosInstance;

    constructor() {
        this.client = createHttpClient('qna/api/v2/chat');
    }

    /**
     * Tạo session chat mới
     *
     * @param sessionName - Tên session (optional)
     * @returns Promise<ChatSession>
     */
    async createSession(sessionName?: string): Promise<ChatResponse> {
        try {
            const response = await this.client.post('/session/create', {
                session_name: sessionName,
            });
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error creating session:', error);
            throw error;
        }
    }

    /**
     * Lấy danh sách sessions của user
     *
     * @returns Promise<ChatSession[]>
     */
    async getSessions(): Promise<ChatResponse> {
        try {
            const response = await this.client.get('/session/list');
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error getting sessions:', error);
            throw error;
        }
    }

    /**
     * Lấy messages trong session
     *
     * @param sessionId - ID của session
     * @param limit - Số messages cần lấy (default: 10)
     * @returns Promise<ChatMessage[]>
     */
    async getSessionMessages(
        sessionId: string,
        limit: number = 10
    ): Promise<ChatResponse> {
        try {
            const response = await this.client.get(
                `/session/${sessionId}/messages?limit=${limit}`
            );
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error getting session messages:', error);
            throw error;
        }
    }

    /**
     * Gửi message trong conversation
     *
     * @param sessionId - ID của session
     * @param question - Câu hỏi của user
     * @param useMemory - Có dùng conversation memory không (default: true)
     * @returns Promise<ChatMessage>
     */
    async sendMessage(
        sessionId: string,
        question: string,
        useMemory: boolean = true,
        messageType: 'query' | 'chitchat' = 'query',
        keywords: string[] = []
    ): Promise<ChatResponse> {
        try {
            const response = await this.client.post('/message/send', {
                session_id: sessionId,
                question: question,
                use_memory: useMemory,
                message_type: messageType,
                keywords,
            });
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    /**
     * Lưu message vào session mà không gọi AI (dùng cho legal_unclear clarification)
     */
    async storeMessage(
        sessionId: string,
        userQuery: string,
        aiResponse: string,
        citations: CitationModel[] = []
    ): Promise<ChatResponse> {
        try {
            const response = await this.client.post('/message/store', {
                session_id: sessionId,
                user_query: userQuery,
                ai_response: aiResponse,
                citations,
            });
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error storing message:', error);
            throw error;
        }
    }

    /**
     * Lấy memory/summary của session
     *
     * @param sessionId - ID của session
     * @returns Promise<ConversationMemory>
     */
    async getSessionMemory(sessionId: string): Promise<ChatResponse> {
        try {
            const response = await this.client.get(
                `/session/${sessionId}/memory`
            );
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error getting session memory:', error);
            throw error;
        }
    }

    /**
     * Clear messages trong session (giữ metadata)
     *
     * @param sessionId - ID của session
     * @returns Promise<void>
     */
    async clearSession(sessionId: string): Promise<ChatResponse> {
        try {
            const response = await this.client.post(
                `/session/${sessionId}/clear`,
                {}
            );
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error clearing session:', error);
            throw error;
        }
    }

    /**
     * Xóa session hoàn toàn
     *
     * @param sessionId - ID của session
     * @returns Promise<void>
     */
    async deleteSession(sessionId: string): Promise<ChatResponse> {
        try {
            const response = await this.client.delete(
                `/session/${sessionId}/delete`
            );
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error deleting session:', error);
            throw error;
        }
    }

    /**
     * Lấy security logs
     *
     * @param limit - Số logs cần lấy (default: 50)
     * @returns Promise<SecurityLog[]>
     */
    async getSecurityLogs(limit: number = 50): Promise<ChatResponse> {
        try {
            const response = await this.client.get(
                `/security/logs?limit=${limit}`
            );
            return response as unknown as ChatResponse;
        } catch (error) {
            console.error('Error getting security logs:', error);
            throw error;
        }
    }
}

export default new ChatService() as ChatService;
