import { formatDate } from '@/utils/common';
import './messageBox.css';
import MarkdownIt from 'markdown-it';
import { CitationModel } from '@/services/chat.service';
import { Card } from 'antd';

export interface MessageBoxProps {
    content: string;
    time: Date;
    isUser: boolean;
    citations?: CitationModel[];
    onCitationClick?: (mapc: string) => void;
}
const md = new MarkdownIt();

export default function MessageBox({ content, time, isUser, citations, onCitationClick }: MessageBoxProps) {
    return (
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
            <div className="message-box">
                <div className={`message ${isUser ? 'user' : 'bot'}`}>
                    <p
                        className="markdown-body"
                        dangerouslySetInnerHTML={{
                            __html: md.render(content),
                        }}
                    ></p>
                </div>
                <div className="flex" style={{ justifyContent: 'end' }}>
                    <em className="time block">{formatDate(time)}</em>
                </div>
            </div>
            
            {/* Citations block rendered only for AI messages that have citations */}
            {!isUser && citations && citations.length > 0 && (
                <div className="w-full mt-4">
                    <h4 className="font-semibold text-gray-500 mb-2 pl-1">
                        Trích dẫn:
                    </h4>
                    <div className="flex gap-4 overflow-x-auto pb-4 snap-x hide-scrollbar max-w-full">
                        {citations.map((item: CitationModel, idx: number) => (
                            <Card
                                key={`${item.mapc}-${idx}`}
                                onClick={() => onCitationClick && onCitationClick(item.mapc)}
                                hoverable
                                className="min-w-[280px] max-w-[320px] h-[200px] flex-shrink-0 snap-start overflow-hidden border border-gray-200 shadow-sm transition-shadow duration-300 rounded-xl"
                                bodyStyle={{ padding: '16px', height: '100%', display: 'flex', flexDirection: 'column' }}
                            >
                                <h4 className="font-semibold text-sm mb-2 text-blue-800 line-clamp-2" title={item.ten}>
                                    {item.ten}
                                </h4>
                                <p className="text-sm text-gray-600 line-clamp-5 flex-1 whitespace-pre-line overflow-hidden text-ellipsis">
                                    {item.noidung}
                                </p>
                            </Card>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
