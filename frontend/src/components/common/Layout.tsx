import { Layout as AntLayout, Menu, Typography, Button, Space } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  CarOutlined,
  DatabaseOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth'

const { Header, Sider, Content } = AntLayout

export function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const selectedKey = location.pathname.startsWith('/requests/create')
    ? '/requests/create'
    : location.pathname.startsWith('/requests')
      ? '/requests/my'
      : location.pathname.startsWith('/approvals')
        ? location.pathname
        : location.pathname.startsWith('/logistics')
          ? location.pathname
          : location.pathname.startsWith('/references/products')
            ? '/references/products'
            : location.pathname.startsWith('/references/objects')
              ? '/references/objects'
              : location.pathname.startsWith('/references')
                ? location.pathname
                : location.pathname

  const canCreate = user?.role === 'commercial' || user?.role === 'logistics'
  const isLogistics = user?.role === 'logistics'

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={64}>
        <div
          style={{
            color: '#fff',
            padding: '16px',
            fontWeight: 600,
            fontSize: 16,
          }}
        >
          Standart Reserve
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/dashboard', icon: <DashboardOutlined />, label: 'Дашборд' },
            { key: '/requests/my', icon: <FileTextOutlined />, label: 'Запросы' },
            ...(canCreate
              ? [
                  {
                    key: '/requests/create',
                    icon: <FileTextOutlined />,
                    label: 'Создать запрос',
                  },
                ]
              : []),
            { key: '/approvals/pp', icon: <CheckSquareOutlined />, label: 'Согласование ПП' },
            {
              key: '/approvals/economy',
              icon: <CheckSquareOutlined />,
              label: 'Согласование экономиста',
            },
            { key: '/normatives', icon: <DatabaseOutlined />, label: 'Нормативы' },
            ...(isLogistics
              ? [
                  {
                    key: '/logistics/dashboard',
                    icon: <CarOutlined />,
                    label: 'Логистика',
                  },
                  {
                    key: '/logistics/one-time',
                    icon: <CarOutlined />,
                    label: 'Разовые перемещения',
                  },
                ]
              : []),
            {
              key: '/references/products',
              icon: <DatabaseOutlined />,
              label: 'Продукты',
            },
            {
              key: '/references/objects',
              icon: <DatabaseOutlined />,
              label: 'Объекты',
            },
          ]}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            padding: '0 24px',
          }}
        >
          <Space>
            <Typography.Text>{user?.full_name ?? 'Гость'}</Typography.Text>
            <Button
              icon={<LogoutOutlined />}
              onClick={async () => {
                await logout()
                navigate('/login')
              }}
            >
              Выйти
            </Button>
          </Space>
        </Header>
        <Content style={{ margin: 24, background: '#fff', padding: 24 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
