import TopNavBar from './components/NavBar';
import Downloader from './components/Downloader';

function App() {
	return (
		<div className="h-screen w-screen flex flex-col bg-gray-100">
			<TopNavBar />
			<Downloader />
			<footer className="mt-auto p-4 bg-white text-center text-sm text-gray-500">
				&copy; 2026 MeTube by James Chan. All rights reserved.
			</footer>
		</div>
	);
}

export default App;
