import { Descendant } from 'slate';
export type TUser = { firstName?: string; position?: string; isVerified?: boolean; image?: { thumb?: string }; };

export type TMail = {
	id: number;
	user: TUser;
	fold: string;
	dateTime: string;
	isNew?: boolean;
	title: string;
	content: Descendant[];
	attachment?: string[];
	flag?: boolean;
};
