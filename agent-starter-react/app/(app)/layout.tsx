import { headers } from 'next/headers';
import { AuthGuard } from '@/components/auth/auth-guard';
import { getAppConfig } from '@/lib/utils';

interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  const hdrs = await headers();
  const { companyName } = await getAppConfig(hdrs);

  return <AuthGuard>{children}</AuthGuard>;
}
