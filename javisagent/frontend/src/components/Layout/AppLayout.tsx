import type { ReactNode } from 'react';
import { Layout } from 'antd';
import SideMenu from './SideMenu';

const { Content } = Layout;

interface AppLayoutProps {
  children: ReactNode;
  onMenuSelect?: (key: string) => void;
  selectedKey?: string;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children, onMenuSelect, selectedKey }) => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <SideMenu onMenuSelect={onMenuSelect} selectedKey={selectedKey} />
      <Layout style={{ flex: 1 }}>
        <Content
          style={{
            margin: '24px',
            padding: '24px',
            background: '#fff',
            borderRadius: '8px',
            minHeight: 280
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
