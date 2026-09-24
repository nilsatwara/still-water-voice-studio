import type { Metadata, Viewport } from 'next';
import './globals.css';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://stillwater.example';

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: 'Stillwater Voice Studio', template: '%s | Stillwater' },
  description: 'Create clear, natural speech with Edge TTS and local Kokoro voices.',
  keywords: ['text to speech', 'Edge TTS', 'Kokoro TTS', 'voice studio', 'audio narration'],
  alternates: { canonical: '/' },
  openGraph: {
    title: 'Stillwater Voice Studio',
    description: 'Natural voice creation with cloud and local speech engines.',
    url: '/',
    siteName: 'Stillwater Voice Studio',
    type: 'website',
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#123f35' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
