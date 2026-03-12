'use client';

import { Button, Card } from 'antd';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { Bounce } from 'react-awesome-reveal';

import chatbot from '@/assets/lottie/chatbot.json';
import law2 from '@/assets/lottie/law2.json';
import law from '@/assets/lottie/law.json';
import form from '@/assets/lottie/form.json';
import feedback from '@/assets/lottie/feedback.json';

const Lottie = dynamic(() => import('lottie-react'), { ssr: false });

const animations = {
    chatbot,
    law2,
    law,
    form,
    feedback,
};

interface HomeNavigationCardProps {
    title: string;
    description: string;
    link: string;
    icon: keyof typeof animations;
}

export default function HomeNavigationCard(props: HomeNavigationCardProps) {
    const router = useRouter();
    const { title, description, link, icon } = props;

    return (
        <Bounce>
            <Card
                hoverable
                onClick={() => router.push(link)}
                title={
                    <h1 style={{ textAlign: 'center', fontSize: 20 }} className="text-lg">
                        {title}
                    </h1>
                }
            >
                <Lottie
                    style={{ width: 200, height: 150, margin: 'auto' }}
                    animationData={animations[icon]}
                />
                <p style={{ height: 50, textAlign: 'center' }}>{description}</p>
                <div style={{ justifyContent: 'center' }} className="flex">
                    <Button className="mt-2" type="primary">
                        Truy Cập
                    </Button>
                </div>
            </Card>
        </Bounce>
    );
}