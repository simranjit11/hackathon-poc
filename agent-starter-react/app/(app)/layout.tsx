import { headers } from 'next/headers';
import { getAppConfig } from '@/lib/utils';
import { AuthGuard } from '@/components/auth/auth-guard';
import { BotIcon } from '@/components/ui/bot-icon';

interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  const hdrs = await headers();
  const { companyName } = await getAppConfig(hdrs);

  return (
    <AuthGuard>
      <header className="fixed top-0 left-0 z-50 hidden w-full flex-row justify-between p-6 md:flex">
        <div className="scale-100 transition-transform duration-300">
          <BotIcon className="size-6" />
        </div>
      </header>

      {children}
    </AuthGuard>
  );
}
