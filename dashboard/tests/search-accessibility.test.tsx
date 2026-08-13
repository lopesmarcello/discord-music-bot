import { renderToStaticMarkup } from 'react-dom/server';
import SearchBar from '../src/components/SearchBar';

const markup = renderToStaticMarkup(<SearchBar guildId="123" />);

if (!markup.includes('aria-label="Search YouTube"')) {
  throw new Error('Track search accessible name must match the visible prompt');
}
