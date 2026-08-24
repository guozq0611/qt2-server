import { FC, ReactNode } from 'react';
import ReactDOM from 'react-dom';

interface IPortalProps {
	children: ReactNode;
	id?: string;
}
// @ts-ignore
const Portal: FC<IPortalProps> = ({ id = 'portal-root', children }) => {
	const mount = document.getElementById(id);
	// @ts-ignore
	if (mount) return ReactDOM.createPortal(children, mount);
	return null;
};

export default Portal;
