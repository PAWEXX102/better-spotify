import { useEffect } from "react"
import { SongPreview } from "./song-preview"

export default function TopSongs({ songs }: { songs: { id: string, feats: [{ id: number, username: string }], title: string, plays: number, duration: string, artist: number, is_indecent: boolean, artistName: string, cover: string }[] }) {

    useEffect(() => {
        console.log(songs)
    }, [songs])
    return (
        <div className=" flex flex-col w-full flex-1 gap-y-2">
            <h1 className=" text-2xl font-semibold text-start">
                Songs
            </h1>
            <div>
                {songs?.map((song, index) => (
                    <SongPreview cover={song.cover} isIndecent={song.is_indecent} artist={song.artistName} key={index} id={song.id} title={song.title} artistId={song.artist} duration={song.duration} plays={song.plays} feats={song.feats} index={index} isDuration={false} isCover isPlays={false} isIndex={false} />
                ))}
            </div>
        </div>
    )
}