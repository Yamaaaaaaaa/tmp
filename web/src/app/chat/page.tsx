'use client';
import MessageBox from '@/components/chat/MessageBox';
import QuestionSideNav from '@/components/chat/QuestionsSidenav';
import { Button, Card, Col, Input, Row } from 'antd';
import './page.css';
import { SendOutlined, PaperClipOutlined } from '@ant-design/icons';
import { useEffect, useState, useRef } from 'react';
import { useAutoAnimate } from '@formkit/auto-animate/react';
import qnaService from '@/services/qna.service';
import chatService, { CitationModel } from '@/services/chat.service';
import { useRouter } from 'next/navigation';

// Typing Indicator Component
const TypingIndicator = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '12px 16px' }}>
        <style>{`
            @keyframes typingBounce {
                0%, 60%, 100% {
                    transform: translateY(0);
                    opacity: 0.7;
                }
                30% {
                    transform: translateY(-10px);
                    opacity: 1;
                }
            }
            .typing-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #60a8f6;
                animation: typingBounce 1.4s infinite;
            }
            .typing-dot:nth-child(2) {
                animation-delay: 0.2s;
            }
            .typing-dot:nth-child(3) {
                animation-delay: 0.4s;
            }
        `}</style>
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
    </div>
);

export interface SelectedQuestion {
    isNew: boolean;
    question?: string;
    answer?: string;
}
interface MessageBox {
    isUser: boolean;
    content: string;
    time: Date;
    citations?: CitationModel[];
}

interface ClarificationOptions {
    baseQuestion: string;
    keywords: string[];
    suggestions?: string[];
}

/*
const mockedData = {
    citation: [
        'Điều 16.1.LQ.125. Tội giết người trong trạng thái tinh thần bị kích động mạnh [(Điều 125 Bộ luật số 100/2015/QH13, có hiệu lực thi hành kể từ ngày 01/01/2018)] 1\\. Người nào giết người trong trạng thái tinh thần bị kích động mạnh do hành vi trái pháp luật nghiêm trọng của nạn nhân đối với người đó hoặc đối với người thân thích của người đó, thì bị phạt tù từ 06 tháng đến 03 năm. 2\\. Phạm tội đối với 02 người trở lên, thì bị phạt tù từ 03 năm đến 07 năm.',
        'Điều 16.1.LQ.123. Tội giết người [(Điều 123 Bộ luật số 100/2015/QH13, có hiệu lực thi hành kể từ ngày 01/01/2018)] 1\\. Người nào giết người thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 12 năm đến 20 năm, tù chung thân hoặc tử hình: a) Giết 02 người trở lên; b) Giết người dưới 16 tuổi; c) Giết phụ nữ mà biết là có thai; d) Giết người đang thi hành công vụ hoặc vì lý do công vụ của nạn nhân; đ) Giết ông, bà, cha, mẹ, người nuôi dưỡng, thầy giáo, cô giáo của mình; e) Giết người mà liền trước đó hoặc ngay sau đó lại thực hiện một tội phạm rất nghiêm trọng hoặc tội phạm đặc biệt nghiêm trọng; g) Để thực hiện hoặc che giấu tội phạm khác; h) Để lấy bộ phận cơ thể của nạn nhân; i) Thực hiện tội phạm một cách man rợ; k) Bằng cách lợi dụng nghề nghiệp; l) Bằng phương pháp có khả năng làm chết nhiều người; m) Thuê giết người hoặc giết người thuê n) Có tính chất côn đồ; o) Có tổ chức; p) Tái phạm nguy hiểm; q) Vì động cơ đê hèn. 2\\. Phạm tội không thuộc các trường hợp quy định tại khoản 1 Điều này, thì bị phạt tù từ 07 năm đến 15 năm. 3\\. Người chuẩn bị phạm tội này, thì bị phạt tù từ 01 năm đến 05 năm. 4\\. Người phạm tội còn có thể bị cấm hành nghề hoặc làm công việc nhất định từ 01 năm đến 05 năm, phạt quản chế hoặc cấm cư trú từ 01 năm đến 05 năm. (Điều này có nội dung liên quan đến [Điều 16.1.LQ.12. Tuổi chịu trách nhiệm hình sự](http://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=); Điều 16.1.LQ.14. Chuẩn bị phạm tội; [Điều 16.1.LQ.91. Nguyên tắc xử lý đối với người dưới 18 tuổi phạm tội](http://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=); [Điều 16.1.LQ.389. Tội che giấu tội phạm của Bộ luật 100/2015/QH13 Hình sự ban hành ngày 27/11/2015](http://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=); Điều 37.7.TT.2.4. Những vụ án hình sự thuộc thẩm quyền của Tòa gia đình và người chưa thành niên xét xử tại Phòng xử án hình sự)',
    ],
    question: 'Quy định xử phạt cho việc vô ý giết người?',
    response: ' 27/11/2015](http://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=);',
    status: 'success',
    topic_ids: ['bcc2a59a-ccbe-4739-afd4-f45811a15122'],
};

const md = new MarkdownIt({ html: true });
*/

export default function Page() {
    const [selectedQuestion, setSelectedQuestion] = useState<SelectedQuestion>({
        isNew: true,
    });
    const [messageBoxes, setMessageBoxes] = useState<MessageBox[]>([]);
    const [search, setSearch] = useState<string>();
    const [loading, setLoading] = useState<boolean>(false);
    const [currentSessionId, setCurrentSessionId] = useState<string>();
    const [refreshSessionsKey, setRefreshSessionsKey] = useState<number>(0);
    const [clarificationOptions, setClarificationOptions] = useState<ClarificationOptions | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadedFileContent, setUploadedFileContent] = useState<string | null>(null);
    const [uploadingFile, setUploadingFile] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [autoAnimateParent] = useAutoAnimate();
    const router = useRouter();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Load messages when session is selected/changed
    useEffect(() => {
        if (currentSessionId) {
            const loadSessionMessages = async () => {
                try {
                    const response = await chatService.getSessionMessages(currentSessionId, 50);
                    if (response?.data && Array.isArray(response.data)) {
                        const messages: MessageBox[] = [];
                        response.data.forEach((msg: any) => {
                            // Add user message
                            messages.push({
                                isUser: true,
                                content: msg.user_query,
                                time: new Date(msg.created_at),
                            });
                            // Add AI response message with citations
                            messages.push({
                                isUser: false,
                                content: msg.ai_response,
                                time: new Date(msg.created_at),
                                citations: msg.citations || [],
                            });
                        });
                        setMessageBoxes(messages);
                    }
                } catch (error) {
                    console.error('Error loading session messages:', error);
                }
            };
            loadSessionMessages();
        }
    }, [currentSessionId]);

    const truncateSessionName = (text: string) => {
        const maxLength = 60;
        if (text.length <= maxLength) return text;
        return `${text.slice(0, maxLength).trim()}...`;
    };

    const ensureSession = async (firstMessage: string) => {
        if (currentSessionId) return currentSessionId;
        const sessionName = truncateSessionName(firstMessage);
        const sessionResponse = await chatService.createSession(sessionName);
        const sessionId = sessionResponse?.data?.session_id;
        if (!sessionId) {
            throw new Error('Failed to create chat session');
        }
        setCurrentSessionId(sessionId);
        setRefreshSessionsKey((prev) => prev + 1);
        return sessionId;
    };

    const send = async () => {
        if (!search) return;

        const userQuery = search;

        // Add user message
        const newUserMessage = {
            isUser: true,
            content: selectedFile 
                ? `${userQuery}\n\n📎 File: ${selectedFile.name}` 
                : userQuery,
            time: new Date(),
        };
        setMessageBoxes(prev => [...prev, newUserMessage]);
        setSearch('');
        removeSelectedFile();
        setLoading(true);

        try {
            // Validate query first
            const validation = await qnaService.validateQuery(userQuery);

            if (!validation || typeof validation !== 'object' || !('type' in validation)) {
                throw new Error('Invalid validation response');
            }

            if (validation.type === 'legal_unclear' && validation.message) {
                const sessionId = await ensureSession(userQuery);
                await chatService.storeMessage(sessionId, userQuery, validation.message, []);
                setMessageBoxes(prev => [...prev, {
                    isUser: false,
                    content: validation.message || '',
                    time: new Date(),
                } as MessageBox]);
                setClarificationOptions({
                    baseQuestion: userQuery,
                    keywords: validation.keywords || [],
                    suggestions: validation.suggestions || [],
                });
                setLoading(false);
                setRefreshSessionsKey((prev) => prev + 1);
                return;
            }

            const messageType = validation.type === 'chitchat' ? 'chitchat' : 'query';
            const useMemory = messageType === 'query';
            const sessionId = await ensureSession(userQuery);

            // Build context with file content if available
            let contextWithFile = userQuery;
            if (uploadedFileContent) {
                contextWithFile = `${userQuery}\n\n[File attached: ${selectedFile?.name || 'file'}]\n${uploadedFileContent}`;
            }

            const chatResponse = await chatService.sendMessage(
                sessionId,
                contextWithFile,
                useMemory,
                messageType,
                validation.keywords || []
            );

            const aiResponse = chatResponse?.data?.ai_response || '';
            const responseCitations = chatResponse?.data?.citations || [];

            setTimeout(() => {
                const newBotMessage: MessageBox = {
                    isUser: false,
                    content: aiResponse,
                    time: new Date(),
                    citations: messageType === 'query' ? responseCitations : [],
                };
                setMessageBoxes(prev => [...prev, newBotMessage]);
                setLoading(false);
                setRefreshSessionsKey((prev) => prev + 1);
                setSelectedQuestion({ isNew: false });
                setClarificationOptions(null);
            }, 300);
        } catch (error) {
            console.error('Error in send function:', error);
            const errorMessage = {
                isUser: false,
                content: 'Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại.',
                time: new Date(),
            };
            setMessageBoxes(prev => [...prev, errorMessage]);
            setLoading(false);
        }
    };

    const handleClarificationChoice = async (mode: 'keyword' | 'skip' | 'suggestion', keywordOrSuggestion?: string) => {
        if (!clarificationOptions) return;

        const base = clarificationOptions.baseQuestion;
        let refinedQuestion = base;

        if (mode === 'keyword' && keywordOrSuggestion) {
            refinedQuestion = `${base}\n(Trọng tâm: ${keywordOrSuggestion})`;
        } else if (mode === 'suggestion' && keywordOrSuggestion) {
            refinedQuestion = `Hỏi thêm về: ${keywordOrSuggestion}`;
        }

        const userMessage = {
            isUser: true,
            content: refinedQuestion,
            time: new Date(),
        };
        setMessageBoxes(prev => [...prev, userMessage]);
        setClarificationOptions(null);
        setLoading(true);

        try {
            const sessionId = await ensureSession(refinedQuestion);
            const chatResponse = await chatService.sendMessage(
                sessionId,
                refinedQuestion,
                true,
                'query',
                mode === 'keyword' && keywordOrSuggestion ? [keywordOrSuggestion] : []
            );

            const aiResponse = chatResponse?.data?.ai_response || '';
            const responseCitations = chatResponse?.data?.citations || [];

            setTimeout(() => {
                const newBotMessage: MessageBox = {
                    isUser: false,
                    content: aiResponse,
                    time: new Date(),
                    citations: responseCitations,
                };
                setMessageBoxes(prev => [...prev, newBotMessage]);
                setLoading(false);
                setRefreshSessionsKey((prev) => prev + 1);
                setSelectedQuestion({ isNew: false });
            }, 300);
        } catch (error) {
            console.error('Error in clarification choice:', error);
            const errorMessage = {
                isUser: false,
                content: 'Xin lỗi, có lỗi xảy ra khi xử lý lựa chọn của bạn. Vui lòng thử lại.',
                time: new Date(),
            };
            setMessageBoxes(prev => [...prev, errorMessage]);
            setLoading(false);
        }
    };
    const goToCitation = (mapc: string) => {
        router.push(`/phapdien?id=${mapc}`);
    };

    const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setSelectedFile(file);
        setUploadingFile(true);
        setUploadError(null);

        try {
            const uploadResponse = await chatService.uploadFile(file);
            
            if (uploadResponse?.data?.content) {
                setUploadedFileContent(uploadResponse.data.content);
                setUploadError(null);
            } else {
                setUploadError('Failed to parse file content');
                setUploadedFileContent(null);
            }
        } catch (error) {
            console.error('File upload error:', error);
            setUploadError(
                error instanceof Error ? error.message : 'Failed to upload file'
            );
            setUploadedFileContent(null);
        } finally {
            setUploadingFile(false);
        }
    };

    const removeSelectedFile = () => {
        setSelectedFile(null);
        setUploadedFileContent(null);
        setUploadError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };
    return (
        <main>
            <Row>
                <Col xs={24} sm={16} md={9} lg={6} xl={4}>
                    <QuestionSideNav
                        setMessageBoxes={setMessageBoxes}
                        setSelectedQuestion={setSelectedQuestion}
                        currentSessionId={currentSessionId}
                        setCurrentSessionId={setCurrentSessionId}
                        refreshKey={refreshSessionsKey}
                    />
                </Col>
                <Col
                    style={{
                        background:
                            'radial-gradient(circle, rgba(240,242,244,1) 0%, rgba(232,241,252,1) 100%)',
                        position: 'relative',
                        height: 'calc(100vh - 107px)',
                        overflow: 'hidden',
                    }}
                    xs={24}
                    sm={8}
                    md={15}
                    lg={18}
                    xl={20}
                >
                    {messageBoxes.length > 0 && (
                        <div
                            ref={autoAnimateParent}
                            style={{
                                margin: 12,
                                height: '100%',
                                overflowY: 'auto',
                                paddingBottom: 80, // chừa chỗ cho thanh gõ
                                display: 'flex',
                                flexDirection: 'column',
                                gap: 16,
                            }}
                        >
                            {messageBoxes.map((messageBox, index) => (
                                <MessageBox
                                    key={index}
                                    isUser={messageBox.isUser}
                                    content={messageBox.content}
                                    time={messageBox.time}
                                    citations={messageBox.citations}
                                    onCitationClick={goToCitation}
                                />
                            ))}

                            {clarificationOptions && (
                                <div>
                                    {/* Keywords section */}
                                    {clarificationOptions.keywords && clarificationOptions.keywords.length > 0 && (
                                        <div
                                            style={{
                                                marginTop: 16,
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: 8,
                                            }}
                                        >
                                            <p style={{ fontSize: '12px', color: '#999', margin: 0 }}>Từ khóa chính:</p>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                                {clarificationOptions.keywords.map((kw) => (
                                                    <Button
                                                        key={kw}
                                                        size="small"
                                                        onClick={() => handleClarificationChoice('keyword', kw)}
                                                    >
                                                        {kw}
                                                    </Button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Suggestions section */}
                                    {clarificationOptions.suggestions && clarificationOptions.suggestions.length > 0 && (
                                        <div
                                            style={{
                                                marginTop: 16,
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: 8,
                                            }}
                                        >
                                            <p style={{ fontSize: '12px', color: '#999', margin: 0 }}>Chủ đề liên quan:</p>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                                {clarificationOptions.suggestions.map((suggestion) => (
                                                    <Button
                                                        key={suggestion}
                                                        size="small"
                                                        type="dashed"
                                                        style={{ cursor: 'pointer' }}
                                                        onClick={() => handleClarificationChoice('suggestion', suggestion)}
                                                    >
                                                        {suggestion}
                                                    </Button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Skip option */}
                                    <div
                                        style={{
                                            marginTop: 12,
                                            display: 'flex',
                                            gap: 8,
                                        }}
                                    >
                                        <Button
                                            size="small"
                                            type="link"
                                            onClick={() => handleClarificationChoice('skip')}
                                        >
                                            Bỏ qua, trả lời theo thông tin hiện tại
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {/* Loading state - Typing indicator */}
                            {loading && (
                                <div
                                    style={{
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        marginTop: 16,
                                    }}
                                >
                                    <div
                                        style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            alignItems: 'flex-start',
                                            width: '100%',
                                        }}
                                    >
                                        <div
                                            style={{
                                                background: 'linear-gradient(90deg, rgba(96, 168, 246, 1) 17%, rgba(94, 167, 246, 1) 19%, rgba(47, 140, 243, 1) 64%)',
                                                borderRadius: '12px',
                                                boxShadow: 'rgba(149, 157, 165, 0.2) 0px 8px 24px',
                                                padding: '8px 12px',
                                                maxWidth: '120px',
                                            }}
                                        >
                                            <TypingIndicator />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    <div
                        style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 8,
                            position: 'absolute',
                            bottom: 0,
                            left: 0,
                            right: 0,
                            padding: '6px 12px',
                        }}
                    >
                        {/* Hidden file input */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                            accept="*"
                        />

                        {/* Selected file display */}
                        {selectedFile && (
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 8,
                                    padding: '6px 12px',
                                    background: uploadError ? '#fff1f0' : uploadingFile ? '#e6f7ff' : '#f0f2f4',
                                    borderRadius: '6px',
                                    fontSize: '13px',
                                    border: uploadError ? '1px solid #ffccc7' : 'none',
                                }}
                            >
                                <PaperClipOutlined 
                                    style={{ 
                                        color: uploadError ? '#ff4d4f' : uploadingFile ? '#1890ff' : '#1890ff',
                                        animation: uploadingFile ? 'spin 1s linear infinite' : 'none'
                                    }} 
                                />
                                <span style={{ color: uploadError ? '#ff4d4f' : 'inherit' }}>
                                    {uploadingFile ? 'Đang upload...' : uploadError ? `❌ ${uploadError}` : selectedFile.name}
                                </span>
                                {!uploadingFile && !uploadError && (
                                    <span style={{ fontSize: '11px', color: '#999' }}>
                                        ({(selectedFile.size / 1024).toFixed(2)} KB)
                                    </span>
                                )}
                                {!uploadingFile && (
                                    <Button
                                        type="text"
                                        size="small"
                                        onClick={removeSelectedFile}
                                        style={{ marginLeft: 'auto', color: uploadError ? '#ff4d4f' : '#999' }}
                                    >
                                        ✕
                                    </Button>
                                )}
                            </div>
                        )}

                        {/* Input section */}
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8,
                                height: 42,
                            }}
                        >
                            <Button
                                onClick={() => fileInputRef.current?.click()}
                                className="h-full"
                                size="large"
                                title="Đính kèm file"
                            >
                                <PaperClipOutlined />
                            </Button>
                            <Input
                                value={search}
                                className="rounded border"
                                placeholder="Hỏi gì đó...."
                                onChange={(event) => setSearch(event.target.value as string)}
                                onKeyUp={(event) => {
                                    if (event.key === 'Enter') {
                                        send();
                                    }
                                }}
                                style={{ flex: 1, height: '100%' }}
                            />
                            <Button onClick={send} type="primary" className="h-full" size="large">
                                <SendOutlined />
                            </Button>
                        </div>
                    </div>
                </Col>
            </Row>
        </main>
    );
}
