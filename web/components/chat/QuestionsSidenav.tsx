'use client';
import { DeleteOutlined, EditOutlined, MessageOutlined } from '@ant-design/icons';
import './sidenav.css';
import { formatDateByString } from '@/utils/common';
import chatService, { ChatSession, CitationModel } from '@/services/chat.service';
import { MessageBoxProps } from './MessageBox';
import { SelectedQuestion } from '@/src/app/chat/page';
import { SetStateAction, useEffect, useState } from 'react';
import { useAutoAnimate } from '@formkit/auto-animate/react';

export interface QuestionSideNavProps {
    setMessageBoxes: React.Dispatch<React.SetStateAction<MessageBoxProps[]>>;
    setSelectedQuestion: React.Dispatch<React.SetStateAction<SelectedQuestion>>;
    currentSessionId?: string;
    setCurrentSessionId: React.Dispatch<React.SetStateAction<string | undefined>>;
    refreshKey: number;
}

export default function QuestionSideNav({
    setMessageBoxes,
    setSelectedQuestion,
    currentSessionId,
    setCurrentSessionId,
    refreshKey,
}: QuestionSideNavProps) {
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [autoAnimateParent] = useAutoAnimate();
    useEffect(() => {
        async function fetchSessions() {
            try {
                const response = await chatService.getSessions();
                const list = response?.data || [];
                list.sort((a: ChatSession, b: ChatSession) => {
                    const aTime = a.last_message_at || a.created_at;
                    const bTime = b.last_message_at || b.created_at;
                    return (bTime || '').localeCompare(aTime || '');
                });
                setSessions(list);
            } catch (error) {
                console.error('Error fetching sessions:', error);
            }
        }
        fetchSessions();
    }, [refreshKey]);

    async function selectSession(sessionId: string) {
        try {
            setSelectedQuestion({ isNew: false });
            setCurrentSessionId(sessionId);
            const response = await chatService.getSessionMessages(sessionId, 50);
            // Be resilient to different response shapes (interceptors may already unwrap)
            const payload: any = response as any;
            const messages =
                (Array.isArray(payload?.data) && payload.data) ||
                (Array.isArray(payload) && payload) ||
                (Array.isArray(payload?.data?.data) && payload.data.data) ||
                [];
            const mapped = messages.map((msg: any) => [
                {
                    isUser: true,
                    content: msg.user_query,
                    time: new Date(msg.created_at),
                },
                {
                    isUser: false,
                    content: msg.ai_response,
                    time: new Date(msg.created_at),
                },
            ]).flat();
            setMessageBoxes(mapped);
        } catch (error) {
            console.error('Error loading session messages:', error);
        }
    }
    function setNewChat() {
        setSelectedQuestion({
            isNew: true,
        });
        setMessageBoxes([]);
        setCurrentSessionId(undefined);
    }

    async function deleteSession(sessionId: string) {
        try {
            await chatService.deleteSession(sessionId);
            setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
            if (currentSessionId === sessionId) {
                setNewChat();
            }
        } catch (error) {
            console.error('Error deleting session:', error);
        }
    }

    return (
        <div
            style={{
                padding: 20,
                color: 'black',
                borderRight: '1px solid #ccc',
                overflowY: 'auto',
                width: '100%',
                height: 'calc(100vh - 107px)',
                paddingTop: 0,
            }}
        >
            <div
                className="flex justify-center sidenav-item"
                style={{
                    justifyContent: 'space-between',
                    borderBottom: '1px solid #ccc',
                    borderRadius: 0,
                    position: 'sticky',
                    top: 0,
                    backgroundColor: 'white',
                    zIndex: 1,
                }}
                onClick={setNewChat}
            >
                <img
                    style={{
                        width: 80,
                        height: 80,
                        borderRadius: '50%',
                    }}
                    src="/LinguTechies.svg"
                    alt="logo"
                />
                <h1 style={{ fontSize: 28, fontWeight: 500, paddingTop: 12 }}>Câu Hỏi Mới</h1>
                <EditOutlined style={{ color: '#5073f3' }} />
            </div>
            <div ref={autoAnimateParent} className="question-container mt-5">
                {sessions.map((session) => (
                    <div
                        key={session.session_id}
                        className="sidenav-item"
                        onClick={() => selectSession(session.session_id)}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: 8,
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                            <MessageOutlined />
                            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
                                <h3 style={{ fontSize: 16, fontWeight: 400, margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {session.session_name || 'Chat Session'}
                                </h3>
                                {session.last_message_at && (
                                    <span className="time">
                                        {formatDateByString(session.last_message_at)}
                                    </span>
                                )}
                            </div>
                        </div>
                        <DeleteOutlined
                            style={{ color: '#ff4d4f' }}
                            onClick={(event) => {
                                event.stopPropagation();
                                deleteSession(session.session_id);
                            }}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}
