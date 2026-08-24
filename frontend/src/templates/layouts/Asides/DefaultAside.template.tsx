import React from 'react';
import Aside, { AsideBody } from '../../../components/layouts/Aside/Aside';
import { appPages } from '../../../config/pages.config';
import Nav, { NavItem, NavTitle } from '../../../components/layouts/Navigation/Nav';
import AsideHeadPart from './_parts/AsideHead.part';
import AsideFooterPart from './_parts/AsideFooter.part';

const DefaultAsideTemplate = () => {
  return (
    <Aside>
      <AsideHeadPart />
      <AsideBody>
        <Nav>
          <NavTitle>行情监控</NavTitle>
          <NavItem {...appPages.dashboardPage} />
          <NavItem {...appPages.tickSnapshotPage} />
          <NavItem {...appPages.instrumentsPage} />
          <NavItem {...appPages.filesPage} />
          <NavItem {...appPages.configPage} />
        </Nav>
      </AsideBody>
      <AsideFooterPart />
    </Aside>
  );
};

export default DefaultAsideTemplate;
