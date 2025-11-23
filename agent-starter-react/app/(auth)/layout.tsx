import { headers } from 'next/headers';
import { BotIcon } from '@/components/ui/bot-icon';
import { getAppConfig } from '@/lib/utils';

interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  const hdrs = await headers();
  const { companyName } = await getAppConfig(hdrs);

  return (
    <>
      <header className="fixed top-0 left-0 z-50 w-full p-6">
        <div className="scale-100 transition-transform duration-300">
          <BotIcon className="size-6" />
        </div>
      </header>
      {children}
    </>
  );
}
