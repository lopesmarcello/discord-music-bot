import { renderToStaticMarkup } from 'react-dom/server';
import SearchBar from '../src/components/SearchBar';

const markup = renderToStaticMarkup(<SearchBar guildId="123" />);

if (!markup.includes('aria-label="Search tracks"')) {
  throw new Error('Track search input has no accessible label');
}
