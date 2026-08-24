import React from 'react';
import Icon from '../../../components/icon/Icon';
import Badge from '../../../components/ui/Badge';
import { NavItem, NavSeparator } from '../../../components/layouts/Navigation/Nav';
import User from '../../../components/layouts/User/User';
import { useAuth } from '../../../context/authContext';

const UserTemplate = () => {
  const { isLoading, userData, onLogout } = useAuth();

  return (
    <User
      isLoading={isLoading}
      name={userData?.firstName || 'Admin'}
      nameSuffix={userData?.isVerified && <Icon icon='HeroCheckBadge' color='blue' />}
      position={userData?.position || 'qt2-server'}
      src={userData?.image?.thumb}
      suffix={
        <Badge color='blue' variant='solid' className='text-xs font-bold'>
          MON
        </Badge>
      }>
      <NavSeparator />
      <NavItem text='Logout' icon='HeroArrowRightOnRectangle' onClick={() => onLogout()} />
    </User>
  );
};

export default UserTemplate;
