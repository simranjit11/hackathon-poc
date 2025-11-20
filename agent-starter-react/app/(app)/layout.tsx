import { headers } from 'next/headers';
import { getAppConfig } from '@/lib/utils';
import { AuthGuard } from '@/components/auth/auth-guard';

interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  const hdrs = await headers();
  const { companyName } = await getAppConfig(hdrs);

  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  );
}
