import React, { createContext, FC, ReactNode, useContext, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import useLocalStorage from '../hooks/useLocalStorage';
import { authPages } from '../config/pages.config';

// 简化的用户类型（qt2-server 监控前端无需复杂用户管理）
export interface TUser {
  firstName?: string;
  position?: string;
  isVerified?: boolean;
  image?: { thumb?: string };
}

export interface IAuthContextProps {
  usernameStorage: string | ((newValue: string | null) => void) | null;
  onLogin: (username: string, password: string) => Promise<void>;
  onLogout: () => void;
  userData: TUser;
  isLoading: boolean;
}
const AuthContext = createContext<IAuthContextProps>({} as IAuthContextProps);

interface IAuthProviderProps {
  children: ReactNode;
}
export const AuthProvider: FC<IAuthProviderProps> = ({ children }) => {
  const [usernameStorage, setUserName] = useLocalStorage('user', null);

  const navigate = useNavigate();

  // 简化：任何非空用户名密码都视为登录成功
  const userData: TUser = useMemo(
    () => ({
      firstName: (usernameStorage as string) || undefined,
      position: 'qt2-server',
      isVerified: true,
    }),
    [usernameStorage],
  );

  const onLogin = async (username: string, _password: string) => {
    if (typeof setUserName === 'function') {
      await setUserName(username);
      navigate('/');
    }
  };

  const onLogout = async () => {
    if (typeof setUserName === 'function') await setUserName(null);
    navigate(`../${authPages.loginPage.to}`, { replace: true });
  };

  const value: IAuthContextProps = useMemo(
    () => ({
      usernameStorage,
      onLogin,
      onLogout,
      userData,
      isLoading: false,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [usernameStorage, userData],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  return useContext(AuthContext);
};
