import { QuestionModel } from '@/models/ChatAnswerModel';
import createHttpClient from '@/utils/createHttpClient';
import createTestHttpClient from '@/utils/createTestHttpClient';
import { AxiosInstance } from 'axios';

export interface QnARequestDto {
    question: string;
}

export interface QnAResponseDto {
    citation: CitationModel[];
    question: string;
    response: string;
    status: string;
}

export interface CitationModel {
    mapc: string;
    noidung: string;
    ten: string;
}

export interface QueryValidationResponse {
    status: string;
    type: 'chitchat' | 'legal_unclear' | 'legal_clear';
    message?: string;
    keywords?: string[];
    suggestions?: string[];
}

class QnAService {
    private client: AxiosInstance;
    private chatClient: AxiosInstance;

    constructor() {
        this.client = createHttpClient('qna/api/v1');
        // Separate client for v2 chat endpoints
        this.chatClient = createHttpClient('qna/api/v2/chat');
        // this.client = createTestHttpClient('/api/v1');
    }

    async answer(body: any) {
        return (await this.client.post('/question', body)) as any;
    }
    
    async createSession(sessionName?: string) {
        try {
            const data = await this.chatClient.post('/session/create', {
                session_name: sessionName,
            });
            return data as unknown as { status: string; data?: { session_id: string; session_name?: string; created_at?: string } };
        } catch (error) {
            console.error('Error creating session:', error);
            throw error;
        }
    }
    
    async sendMessage(
        sessionId: string,
        question: string,
        useMemory: boolean = true,
        messageType: 'query' | 'chitchat' = 'query'
    ) {
        try {
            const data = await this.chatClient.post('/message/send', {
                session_id: sessionId,
                question: question,
                use_memory: useMemory,
                message_type: messageType,
            });
            return data as unknown as any;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }
    
    async validateQuery(question: string): Promise<QueryValidationResponse> {
        try {
            // Note: createHttpClient interceptor already returns res.data
            // so response here is already the data object, not axios response
            const data = await this.client.post('/validate-query', {
                question: question,
            });
            
            if (!data || typeof data !== 'object' || !('type' in data)) {
                console.error('Invalid validation response:', data);
                throw new Error('Invalid response structure from validation endpoint');
            }
            
            return data as unknown as QueryValidationResponse;
        } catch (error) {
            console.error('Error validating query:', error);
            throw error;
        }
    }

    async getQuestions() {
        return (await this.client.get('/question')) as QuestionModel[];
    }
}

export default new QnAService() as QnAService;
