import React, { useState } from 'react';
import Icon from '../../../../components/icon/Icon';
import { appPages } from '../../../../config/pages.config';

const SearchPartial = () => {
  const [query, setQuery] = useState('');

  const pages = Object.values(appPages).filter((p: any) =>
    p.text?.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className='relative'>
      <div className='flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-1.5 dark:border-zinc-700'>
        <Icon icon='HeroMagnifyingGlass' color='zinc' />
        <input
          type='text'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='搜索页面...'
          className='w-40 bg-transparent text-sm outline-none'
        />
      </div>
      {query && (
        <div className='absolute top-full left-0 z-50 mt-1 w-56 rounded-lg border border-zinc-200 bg-white py-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-800'>
          {pages.length === 0 ? (
            <div className='px-3 py-2 text-sm text-zinc-400'>无匹配结果</div>
          ) : (
            pages.map((p: any) => (
              <a
                key={p.id}
                href={p.to}
                className='block px-3 py-1.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-700'>
                {p.text}
              </a>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default SearchPartial;
