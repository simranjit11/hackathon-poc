'use client';

import { useState } from 'react';
import { RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionProvider } from '@/components/app/session-provider';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/livekit/toaster';
import { useAuth } from '@/components/auth/auth-provider';
import { Button } from '@/components/livekit/button';
import { ContactsSidebar } from '@/components/app/contacts-sidebar';
import { Users } from 'lucide-react';

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const { user, logout } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <SessionProvider appConfig={appConfig}>
      <ContactsSidebar 
        isOpen={isSidebarOpen} 
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)} 
      />
      
      {/* Contacts Button - Only visible when sidebar is closed */}
      {!isSidebarOpen && (
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="fixed left-6 top-6 z-50 flex items-center gap-2 rounded-lg bg-accent px-4 py-2 shadow-lg transition-all hover:bg-accent/80"
          aria-label="Open contacts"
        >
          <Users className="size-5" />
          <span className="text-sm font-medium">Contacts</span>
        </button>
      )}

      <main className="grid h-svh grid-cols-1 place-content-center">
        <div className="fixed top-6 right-6 z-50">
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground text-sm">
              {user?.email}
            </span>
            <Button variant="outline" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
        <ViewController />
      </main>
      <StartAudio label="Start Audio" />
      <RoomAudioRenderer />
      <Toaster />
    </SessionProvider>
  );
}
