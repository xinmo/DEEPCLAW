import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import { FileText, Settings, User, Cog, ChevronLeft, ChevronRight } from 'lucide-react';

const { Sider } = Layout;

const SideMenu: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Sider 
      width={200} 
      collapsed={collapsed}
      collapsedWidth={64}
      style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}
      trigger={null}
    >
      <div style={{ 
        padding: collapsed ? '16px 8px' : '16px', 
        fontSize: collapsed ? '14px' : '18px', 
        fontWeight: 'bold', 
        color: '#1890ff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        height: '64px',
        borderBottom: '1px solid #f0f0f0'
      }}>
        {!collapsed && 'JAVISAGENT'}
      </div>
      <Menu
        mode="inline"
        defaultSelectedKeys={['document-parse']}
        defaultOpenKeys={['smart-parse']}
        style={{ height: 'calc(100% - 64px)', borderRight: 0 }}
        items={[
          {
            key: 'smart-parse',
            label: collapsed ? '' : '智能解析',
            icon: <FileText size={16} />,
            children: [
              {
                key: 'document-parse',
                label: collapsed ? '' : '文档解析',
                icon: <FileText size={16} />
              }
            ]
          },
          {
            key: 'settings',
            label: collapsed ? '' : '设置',
            icon: <Settings size={16} />,
            children: [
              {
                key: 'account-settings',
                label: collapsed ? '' : '账户设置',
                icon: <User size={16} />
              },
              {
                key: 'system-settings',
                label: collapsed ? '' : '系统设置',
                icon: <Cog size={16} />
              }
            ]
          }
        ]}
      />
      <div 
        style={{
          position: 'absolute',
          right: -12,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 24,
          height: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#fff',
          borderRadius: '50%',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          cursor: 'pointer',
          zIndex: 10
        }}
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </div>
    </Sider>
  );
};

export default SideMenu;
