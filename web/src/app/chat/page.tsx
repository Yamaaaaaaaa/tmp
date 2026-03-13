'use client';
import MessageBox from '@/components/chat/MessageBox';
import QuestionSideNav from '@/components/chat/QuestionsSidenav';
import { Button, Card, Col, Input, Row } from 'antd';
import './page.css';
import { SendOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { useAutoAnimate } from '@formkit/auto-animate/react';
import qnaService from '@/services/qna.service';
import chatService, { CitationModel } from '@/services/chat.service';
import { useRouter } from 'next/navigation';
export interface SelectedQuestion {
    isNew: boolean;
    question?: string;
    answer?: string;
}
interface MessageBox {
    isUser: boolean;
    content: string;
    time: Date;
}

interface ClarificationOptions {
    baseQuestion: string;
    keywords: string[];
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
    const [citations, setCitations] = useState<CitationModel[]>([]);
    const [search, setSearch] = useState<string>();
    const [loading, setLoading] = useState<boolean>(false);
    const [currentSessionId, setCurrentSessionId] = useState<string>();
    const [refreshSessionsKey, setRefreshSessionsKey] = useState<number>(0);
    const [clarificationOptions, setClarificationOptions] = useState<ClarificationOptions | null>(null);
    const [autoAnimateParent] = useAutoAnimate();
    const router = useRouter();

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
        
        // Add user message immediately and preserve history
        const newUserMessage = {
            isUser: true,
            content: userQuery,
            time: new Date(),
        };
        setMessageBoxes(prev => [...prev, newUserMessage]);
        setSearch('');
        setLoading(true);

        try {
            // Step 1: Validate query
            console.log('Sending validation request for query:', userQuery);
            const validation = await qnaService.validateQuery(userQuery);
            
            console.log('Query validation result:', validation);
            
            // Ensure validation has expected structure
            if (!validation || typeof validation !== 'object' || !('type' in validation)) {
                console.error('Invalid validation response structure:', validation);
                throw new Error('Invalid validation response');
            }
            
            if (validation.type === 'legal_unclear' && validation.message) {
                // If query is unclear legal question, ask for clarification AND persist to session
                // so the next user turn has memory of what they asked.
                const sessionId = await ensureSession(userQuery);
                await chatService.storeMessage(sessionId, userQuery, validation.message, []);

                const clarificationMessage = {
                    isUser: false,
                    content: validation.message,
                    time: new Date(),
                };
                setMessageBoxes(prev => [...prev, clarificationMessage]);
                setClarificationOptions({
                    baseQuestion: userQuery,
                    keywords: validation.keywords || [],
                });
                setLoading(false);
                setRefreshSessionsKey((prev) => prev + 1);
                return;
            }

            const messageType = validation.type === 'chitchat' ? 'chitchat' : 'query';
            const useMemory = messageType === 'query';
            const sessionId = await ensureSession(userQuery);

            const chatResponse = await chatService.sendMessage(
                sessionId,
                userQuery,
                useMemory,
                messageType,
                validation.keywords || []
            );

            const aiResponse = chatResponse?.data?.ai_response || '';
            const responseCitations = chatResponse?.data?.citations || [];
            setCitations(messageType === 'query' ? responseCitations : []);

            setTimeout(() => {
                const newBotMessage = {
                    isUser: false,
                    content: aiResponse,
                    time: new Date(),
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

    const handleClarificationChoice = async (mode: 'keyword' | 'skip', keyword?: string) => {
        if (!clarificationOptions) return;

        const base = clarificationOptions.baseQuestion;
        const refinedQuestion =
            mode === 'keyword' && keyword ? `${base}\n(Trọng tâm: ${keyword})` : base;

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
                mode === 'keyword' && keyword ? [keyword] : []
            );

            const aiResponse = chatResponse?.data?.ai_response || '';
            const responseCitations = chatResponse?.data?.citations || [];
            setCitations(responseCitations);

            setTimeout(() => {
                const newBotMessage = {
                    isUser: false,
                    content: aiResponse,
                    time: new Date(),
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
    return (
        <main>
            <Row>
                <Col xs={24} sm={16} md={10} lg={6} xl={5}>
                    <QuestionSideNav
                        setMessageBoxes={setMessageBoxes}
                        setCitations={setCitations}
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
                    md={14}
                    lg={18}
                    xl={19}
                >
                    {messageBoxes.length > 0 && (
                        <div
                            ref={autoAnimateParent}
                            style={{
                                margin: 12,
                                height: '100%',
                                overflowY: 'auto',
                                paddingBottom: 80, // chừa chỗ cho thanh gõ
                            }}
                        >
                            {messageBoxes.map((messageBox, index) => (
                                <MessageBox
                                    key={index}
                                    isUser={messageBox.isUser}
                                    content={messageBox.content}
                                    time={messageBox.time}
                                />
                            ))}

                            {clarificationOptions && (
                                <div
                                    style={{
                                        marginTop: 16,
                                        display: 'flex',
                                        flexWrap: 'wrap',
                                        gap: 8,
                                    }}
                                >
                                    {clarificationOptions.keywords.map((kw) => (
                                        <Button
                                            key={kw}
                                            size="small"
                                            onClick={() => handleClarificationChoice('keyword', kw)}
                                        >
                                            {kw}
                                        </Button>
                                    ))}
                                    <Button
                                        size="small"
                                        type="link"
                                        onClick={() => handleClarificationChoice('skip')}
                                    >
                                        Bỏ qua, cứ trả lời theo thông tin hiện tại
                                    </Button>
                                </div>
                            )}
                            
                            {/* Loading state for validation or processing */}
                            {loading && (
                                <div
                                    style={{
                                        padding: '16px',
                                        textAlign: 'center',
                                        color: '#999',
                                        fontSize: '14px',
                                        marginTop: '12px',
                                    }}
                                >
                                    <span style={{ animation: 'pulse 1.5s infinite' }}>
                                        Đang xử lý...
                                    </span>
                                </div>
                            )}
                            
                            {citations?.length > 0 && (
                                <h4 style={{ color: '#ccc', marginTop: 24 }} className="text-2xl">
                                    Trích dẫn
                                </h4>
                            )}
                            <Row gutter={[16, 16]}>
                                {citations?.map((item: CitationModel) => (
                                    <Col key={item.mapc} xs={24} sm={12} md={12} lg={8} xl={5}>
                                        <Card
                                            style={{ padding: '12px 0' }}
                                            onClick={() => goToCitation(item.mapc)}
                                            className="max-h-[300px] overflow-hidden text-ellipsis py-5"
                                            hoverable
                                            title={item.ten}
                                        >
                                            <p
                                                style={{
                                                    whiteSpace: 'pre-line',
                                                }}
                                                className="h-full"
                                            >
                                                {item.noidung}
                                            </p>
                                        </Card>
                                    </Col>
                                ))}
                            </Row>
                        </div>
                    )}
                    <div
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            position: 'absolute',
                            bottom: 0,
                            left: 0,
                            right: 0,
                            padding: '6px 12px',
                            height: 60,
                        }}
                    >
                        <Input
                            value={search}
                            className="w-full rounded h-full border"
                            placeholder="Hỏi gì đó...."
                            onChange={(event) => setSearch(event.target.value as string)}
                            onKeyUp={(event) => {
                                if (event.key === 'Enter') {
                                    send();
                                }
                            }}
                        />
                        <Button onClick={send} type="primary" className="h-full" size="large">
                            <SendOutlined />
                        </Button>
                    </div>
                </Col>
            </Row>
        </main>
    );
}
