import { useState, useRef } from 'react';
import type { ChangeEvent } from 'react';
import type {
	VideoInfo,
	DownloadRequest,
	DownloadJob,
	ProgressData,
	ErrorResponse,
	FormatType,
	OutputFormat,
} from '@/types';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Field, FieldLabel } from '@/components/ui/field';
import {
	Select,
	SelectContent,
	SelectGroup,
	SelectItem,
	SelectLabel,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { API_BASE_URL, formatDuration, formatBytes, parseProgress, downloadFileHandler } from '@/utils';
import { fetchVideoInfo, downloadVideo, jobCleanup } from '@/apis';

export default function Downloader() {
	const [url, setUrl] = useState<string>('');
	const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
	const [selectedQuality, setSelectedQuality] = useState<FormatType>('best');
	const [selectedFormat, setSelectedFormat] = useState<OutputFormat>('original');
	const [jobId, setJobId] = useState<string | null>(null);
	const [progress, setProgress] = useState<ProgressData | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState<boolean>(false);

	const eventSourceRef = useRef<EventSource | null>(null);

	const urlHandler = (e: ChangeEvent<HTMLInputElement>) => {
		setUrl(e.target.value);
	};

	const qualityHandler = (value: FormatType) => {
		setSelectedQuality(value);
	};

	const formatHandler = (value: OutputFormat) => {
		setSelectedFormat(value);
	};

	const reset = () => {
		setUrl('');
		setVideoInfo(null);
		setSelectedQuality('best');
		setSelectedFormat('original');
		setJobId(null);
		setProgress(null);
		setError(null);
		setLoading(false);
	};

	const handleFetchInfo = async (): Promise<void> => {
		if (!url) {
			setError('Please enter a YouTube URL');
			return;
		}

		if (jobId) {
			await handleCleanup(true);
		}

		setLoading(true);
		setError(null);
		setVideoInfo(null);

		try {
			const response = await fetchVideoInfo(url);

			if (!response.ok) {
				const errorData: ErrorResponse = await response.json();
				throw new Error(errorData.detail || 'Failed to fetch video info');
			}

			const data: VideoInfo = await response.json();
			setVideoInfo(data);
		}
		catch (err) {
			setError(err instanceof Error ? err.message : 'Unknown error occurred');
		}
		finally {
			setLoading(false);
		}
	};
    
	const handleStartDownload = async (): Promise<void> => {
		if (!url) {
			setError('Please enter a YouTube URL');
			return;
		}

		setLoading(true);
		setError(null);
		setProgress(null);

		try {
			const downloadVideoOpts: DownloadRequest = {
				url,
				format: selectedQuality,
				output_format: selectedFormat,
			};
			const response = await downloadVideo(downloadVideoOpts);

			if (!response.ok) {
				const errorData: ErrorResponse = await response.json();
				throw new Error(errorData.detail || 'Failed to start download');
			}

			const data: DownloadJob = await response.json();
			setJobId(data.job_id);
			startProgressStream(data.job_id);
		}
		catch (err) {
			setError(err instanceof Error ? err.message : 'Unknown error occurred');
			setLoading(false);
		}
	};

	// Listen to SSE progress updates
	const startProgressStream = (jobId: string): void => {
		// Close existing connection if any
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
		}

		const eventSource = new EventSource(`${API_BASE_URL}/api/download/progress/${jobId}`);
		eventSourceRef.current = eventSource;

		eventSource.addEventListener('progress', (event: Event) => {
			const messageEvent = event as MessageEvent;
			try {
				const progressData: ProgressData = parseProgress(messageEvent.data);
				setProgress(progressData);

				if (progressData.status === 'completed') {
					setLoading(false);
					eventSource.close();
				}
				else if (progressData.status === 'error') {
					setError(progressData.message || 'Download failed');
					setLoading(false);
					eventSource.close();
				}
			}
			catch (err) {
				console.error('Failed to parse progress data:', err);
			}
		});

		eventSource.addEventListener('close', () => {
			eventSource.close();
		});

		eventSource.onerror = (err: Event) => {
			console.error('EventSource error:', err);
			setError('Connection error. Please try again.');
			setLoading(false);
			eventSource.close();
		};
	};

	const handleDownloadFile = (): void => {
		if (!jobId) return;

		downloadFileHandler(jobId, progress?.filename || 'video');
	};

	const handleCleanup = async (keepUrl?: boolean): Promise<void> => {
		if (!jobId) return;

		try {
			await jobCleanup(jobId);
			setJobId(null);
			setProgress(null);
			setVideoInfo(null);

			if (!keepUrl) {
				setUrl('');
			}
		}
		catch (err) {
			console.error('Cleanup error:', err);
		}
	};
	return (
		<div className="flex flex-col items-center justify-center gap-8 bg-gray-100 mt-8">
			<h1 className="text-3xl font-bold">MeTube - a simple youtube downloader</h1>
			<div className="w-full max-w-2xl">
				<Field orientation="horizontal">
					<Input
						type="text"
						className="text-base max-w-2xl w-full h-12 placeholder:text-lg"
						style={{ fontSize: '18px' }}
						placeholder="Enter or paste link here..."
						value={url}
						onChange={urlHandler}
					/>
					<Button
						variant="outline"
						className="w-24 h-12 cursor-pointer"
						style={{ fontSize: '18px' }}
						onClick={handleFetchInfo}
						disabled={!url || loading || error !== null}
					>
						Start
					</Button>
				</Field>
			</div>
			{error && (
				<>
					<div className="errorMsg text-sm flex flex-col gap-2 justify-center">
						<div className="text-red-500">
							Error:
							{' '}
							{error}
						</div>
						<div>Please check the URL and try again.</div>
					</div>
					<Button
						variant="outline"
						className="w-24 cursor-pointer"
						style={{ fontSize: '18px' }}
						onClick={reset}
					>
						Retry
					</Button>
				</>
			)}
			{videoInfo && (
				<div>
					<div className="flex flex-col gap-4 justify-center">
						<img src={videoInfo.thumbnail} alt={videoInfo.title} className="max-w-md h-auto" />
						<div>
							<h2 className="text-2xl max-w-md text-slate-600">{videoInfo.title}</h2>
							<div className="flex justify-between max-w-md text-lg">
								<p>
									<strong>Uploader:</strong>
									{' '}
									{videoInfo.uploader}
								</p>
								<p>
									<strong>Duration:</strong>
									{' '}
									{formatDuration(videoInfo.duration)}
								</p>
							</div>
						</div>
						<div className="text-lg">
							<label>Quality:</label>
							<Select defaultValue="best" onValueChange={qualityHandler}>
								<SelectTrigger className="w-full max-w-48">
									<SelectValue placeholder="Select a quality" />
								</SelectTrigger>
								<SelectContent>
									<SelectGroup>
										<SelectLabel>Quality</SelectLabel>
										<SelectItem value="best">Best Quality</SelectItem>
										{(videoInfo.formats || []).map(format => (
											format.has_filesize
											&& (
												<SelectItem
													key={format.format_id}
													value={format.resolution}
												>
													{format.resolution}
												</SelectItem>
											)
										))}
										<SelectItem value="audio">Audio Only (MP3)</SelectItem>
									</SelectGroup>
								</SelectContent>
							</Select>
						</div>

						<div className="text-lg">
							<label>Format:</label>
							<Select defaultValue="original" onValueChange={formatHandler} disabled={selectedQuality === 'audio'}>
								<SelectTrigger className="w-full max-w-48">
									<SelectValue placeholder="Select a format" />
								</SelectTrigger>
								<SelectContent>
									<SelectGroup>
										<SelectLabel>Format</SelectLabel>
										<SelectItem value="original">Original</SelectItem>
										<SelectItem value="mp4">MP4</SelectItem>
										<SelectItem value="webm">WebM</SelectItem>
									</SelectGroup>
								</SelectContent>
							</Select>
						</div>
						<Button
							variant="outline"
							className="cursor-pointer"
							style={{ backgroundColor: '#349ccc', color: 'white', fontSize: '18px' }}
							onClick={handleStartDownload}
							disabled={loading}
						>
							{loading ? 'Processing...' : 'Start Download'}
						</Button>
					</div>
				</div>
			)}
			{progress && (
				<div className="w-full max-w-2xl">
					<Field>
						<FieldLabel htmlFor="progress-download">
							<span className="text-base">Downloading...</span>
							<span className="ml-auto text-base">
								{progress.percentage?.toFixed(1)}
								%
							</span>
						</FieldLabel>
						<Progress value={progress.percentage || 0} id="progress-download" />
						<div className="text-lg mt-4">
							<p>
								<strong>Status:</strong>
								{' '}
								{progress.status}
							</p>
							{progress.downloaded && (
								<p>
									<strong>Downloaded:</strong>
									{' '}
									{formatBytes(progress.downloaded)}
									{' '}
									/
									{' '}
									{formatBytes(progress.total)}
								</p>
							)}
							{progress.speed && (
								<p>
									<strong>Speed:</strong>
									{' '}
									{formatBytes(progress.speed)}
									/s
								</p>
							)}
							{progress.eta && (
								<p>
									<strong>ETA:</strong>
									{' '}
									{progress.eta}
									s
								</p>
							)}
							{progress.message && (
								<p>
									<strong>Message:</strong>
									{' '}
									{progress.message}
								</p>
							)}
						</div>
					</Field>
					{progress.status === 'completed' && (
						<div className="flex gap-2 mt-4">
							<Button
								variant="outline"
								className="cursor-pointer"
								style={{ backgroundColor: '#4CAF50', color: 'white', fontSize: '18px' }}
								onClick={handleDownloadFile}
							>
								Download File
							</Button>
							<Button
								variant="outline"
								className="cursor-pointer"
								style={{ backgroundColor: '#818181', color: 'white', fontSize: '18px' }}
								onClick={() => handleCleanup(false)}
							>
								Start New Download
							</Button>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
