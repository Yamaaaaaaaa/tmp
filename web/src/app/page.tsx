'use client';
import dynamic from 'next/dynamic';
import HomeNavigationCard from '@/components/home/HomeNavigationCard';
import { Col, Input, Row, Spin } from 'antd';
const { Search } = Input;
import { useEffect, useState, useRef } from 'react';
import { Fade } from 'react-awesome-reveal';
import vbqpplService from '@/services/vbqppl.service';

const Lottie = dynamic(() => import('lottie-react'), { 
  ssr: false,
  loading: () => <Spin size="large" />
});
export default function Home() {
    const [animationData, setAnimationData] = useState<any>(null);
    const [searchResult, setSearchResult] = useState<any[]>([]);
    const [loadingRecommend, setLoadingRecommend] = useState(false);
    const resultRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        import(`@/assets/lottie/law.json`).then((data) => {
            setAnimationData(data.default);
        });
    }, []);
    if (!animationData) {
        return (
            <div className="w-full p-5 flex justify-center">
                <Spin size="large"></Spin>
            </div>
        );
    }

    const search = async (value: string) => {
        setLoadingRecommend(true);
        const result: any = await vbqpplService.getReccomended({
            keyword: value,
            num_of_relevant_texts: 7,
        });

        for (const id of result.text_ids) {
            const vb = await vbqpplService.getOne(id);
            console.log(vb);
        }

        setSearchResult(result);
        setLoadingRecommend(false);
        setTimeout(() => {
            if (resultRef.current) {
                resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 300);
    };
    return (
        <>
            <Fade>
                <Row className="wavy h-[450px] w-full" justify="center" align="middle">
                    <Col span={8}>
                        <Lottie animationData={animationData} className="w-[450px]" />
                    </Col>
                    <Col span={10}>
                        <h1 style={{ color: 'white' }} className="text-5xl font-bold">
                            VN Law Advisor
                        </h1>
                        <p style={{ color: 'white' }} className="text-2xl italic mt-2">
                            Hệ thống hỏi đáp tri thức pháp luật Việt Nam
                        </p>
                        <ul style={{ color: 'white' }} className="mt-3">
                            <li className="italic text-xl list-disc">
                                Dựa trên mô hình ngôn ngữ lớn.
                            </li>
                            <li className="mt-1 italic text-xl list-disc">
                                Tri thức từ pháp điển Việt Nam và các VBQPPL.
                            </li>
                        </ul>
                    </Col>
                </Row>
            </Fade>
            <main className="flex flex-col items-center justify-between my-5 p-x-24">
                <div>
                    <Row justify="start">
                        <Col span={24}>
                            <h1 style={{ margin: '16px 0' }}>Tìm văn bản pháp luật bằng từ khóa</h1>

                            <Search
                                placeholder="Tìm một từ khóa..."
                                onSearch={search}
                                enterButton
                            />
                        </Col>
                        <Col span={24}></Col>
                    </Row>
                </div>
                <h1 className="text-3xl my-5">Nổi Bật</h1>
                <div className="">
                    <Row justify="center" gutter={[16, 16]}>
                        <Col span={4} lg={4} md={6} sm={8} xs={24}>
                            <HomeNavigationCard
                                link="/chat"
                                title="Hỏi đáp Pháp Luật"
                                description="Trợ lý AI giải đáp các câu hỏi về pháp luật Việt Nam."
                                icon="chatbot"
                            />
                        </Col>
                        <Col span={4} lg={4} md={6} sm={8} xs={24}>
                            <HomeNavigationCard
                                link="/phapdien"
                                title="Tra cứu Pháp Điển"
                                description="Tra cứu Pháp Điển Việt Nam hiện hành."
                                icon="law2"
                            />
                        </Col>
                        <Col span={4} lg={4} md={6} sm={8} xs={24}>
                            <HomeNavigationCard
                                link="/vbqppl"
                                title="Tra cứu các VBQPPL"
                                description="Tra cứu các điều luật từ VBQPPL Việt Nam."
                                icon="law"
                            />
                        </Col>
                        <Col span={4} lg={4} md={6} sm={8} xs={24}>
                            <HomeNavigationCard
                                link="/form"
                                title="Các bảng, biểu mẫu"
                                description="Tra cứu các bảng và biểu mẫu từ VBQPPL."
                                icon="form"
                            />
                        </Col>
                        <Col span={4} lg={4} md={6} sm={8} xs={24}>
                            <HomeNavigationCard
                                link="/chat"
                                title="Đánh giá, góp ý"
                                description="Gửi ý kiến của bạn, cải thiện gợi ý hệ thống."
                                icon="feedback"
                            />
                        </Col>
                    </Row>
                </div>
                {/* Indicator loading recommend */}
                {loadingRecommend && (
                    <div style={{ width: '100%', display: 'flex', justifyContent: 'center', margin: '24px 0' }}>
                        <Spin size="large" tip="Đang tìm kiếm..." />
                    </div>
                )}
                {/* Hiển thị kết quả tìm kiếm recommend */}
                {searchResult?.text_topics && searchResult.text_topics.length > 0 && (
                    <div ref={resultRef} style={{ margin: '32px 0' }}>
                        <h2 style={{ fontSize: 22, marginBottom: 16, color: '#1677ff' }}>Kết quả liên quan</h2>
                        <Row gutter={[16, 16]} justify="start">
                            {searchResult.text_topics.map((topic: any, idx: number) => (
                                <Col key={idx} xs={24} sm={12} md={8} lg={6} xl={6}>
                                    <div style={{
                                        border: '1px solid #e0e0e0',
                                        borderRadius: 12,
                                        padding: 18,
                                        background: '#f7faff',
                                        boxShadow: '0 2px 8px rgba(22,119,255,0.08)',
                                        minHeight: 180,
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: 8,
                                    }}>
                                        <div style={{ fontWeight: 600, color: '#333' }}>
                                            <span style={{ color: '#1677ff' }}>ID VB:</span> {topic.id_vb}
                                        </div>
                                        <div style={{ color: '#555' }}>
                                            <span style={{ color: '#1677ff' }}>ID:</span> {topic.id}
                                        </div>
                                        <div style={{ color: '#888', fontSize: 13 }}>
                                            <span style={{ color: '#1677ff' }}>Chỉ mục cha:</span> {topic.chi_muc_cha || <i>Không có</i>}
                                        </div>
                                        <div style={{ color: '#222', fontSize: 15, marginTop: 8 }}>
                                            <span style={{ color: '#1677ff', fontWeight: 500 }}>Trích dẫn:</span>
                                            <div style={{
                                                background: '#fff',
                                                borderRadius: 8,
                                                padding: '8px 12px',
                                                marginTop: 4,
                                                fontStyle: 'italic',
                                                color: '#1a237e',
                                                boxShadow: '0 1px 4px rgba(22,119,255,0.05)',
                                            }}>
                                                {topic.citation}
                                            </div>
                                        </div>
                                    </div>
                                </Col>
                            ))}
                        </Row>
                    </div>
                )}
            </main>
        </>
    );
}
