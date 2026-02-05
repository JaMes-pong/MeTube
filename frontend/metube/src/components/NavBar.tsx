import { TvMinimalPlay, ArrowBigRightDash, SquarePlay } from 'lucide-react';

export default function TopNavBar() {
	return (
		<nav className="bg-white shadow-md">
			<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<div className="flex justify-between items-center h-16">
					<div className="flex-shrink-0 flex items-center">
						<SquarePlay className="h-8 w-8 text-red-600 mr-2" />
						<ArrowBigRightDash className="h-8 w-8 text-blue-500 mr-2" />
						<TvMinimalPlay className="h-8 w-8 text-slate-600 mr-2" />
						<h2 className="text-2xl font-bold text-gray-800 ml-4">MeTube Downloader</h2>
					</div>
				</div>
			</div>
		</nav>
	);
}
