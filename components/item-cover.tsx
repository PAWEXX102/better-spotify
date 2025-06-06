"use client";
import Image from "next/image";
import { Pause, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "./ui/skeleton";
import { useState } from "react";
import { useCurrentSongStore } from "@/store/current-song";
import { motion } from "framer-motion";
import { LoaderCircle } from "lucide-react";



export const PlayAnimation = ({ isPlaying }: { isPlaying: boolean }) => {
  if (!isPlaying) return null;
  return (
    <div className=" flex space-x-1 group-hover:hidden items-center justify-center">
      <motion.div
        initial={{ scaleY: 0.4 }}
        animate={{
          scaleY: isPlaying ? 1 : 0.4,
          transition: {
            duration: 0.5,
            ease: "easeInOut",
            repeat: Infinity,
            repeatType: "reverse",
          },
        }}
        className="w-[5px] h-[20px] origin-center rounded-full bg-black"
      />
      <motion.div
        initial={{ scaleY: 0.4 }}
        animate={{
          scaleY: isPlaying ? 1 : 0.4,
          transition: {
            duration: 0.5,
            ease: "easeInOut",
            repeat: Infinity,
            repeatType: "reverse",
            delay: 0.5,
          },
        }}
        className="w-[5px] h-[20px] origin-center rounded-full bg-black"
      />
      <motion.div
        initial={{ scaleY: 0.4 }}
        animate={{
          scaleY: isPlaying ? 1 : 0.4,
          transition: {
            duration: 0.5,
            ease: "easeInOut",
            repeat: Infinity,
            repeatType: "reverse",
          },
        }}
        className="w-[5px] h-[20px] origin-center rounded-full bg-black"
      />
    </div>
  );
};

export default function ItemCover({
  title = "4x4",
  artist,
  artistID,
  cover = "/cover.jpg",
  type = "album",
  setHover = () => { },
  songs = [],
  theme = "dark",
  id = 1,
}: {
  title?: string;
  artistID?: string;
  theme?: string;
  cover?: string;
  songs?: { id: number }[];
  artist?: string;
  setHover?: (hover: string) => void;
  id?: number;
  type?: string;
}) {
  const router = useRouter();
  const [isHover, setIsHover] = useState(false);
  const handleClick = () => {
    router.push(
      `/${type === "album" || type === "ep" ? "album" : type === "song" ? "song" : "profile"
      }/${id}`
    );
  };
  const setCurrentSongID = useCurrentSongStore((state) => state.setCurrentSongID);
  const currentSongID = useCurrentSongStore((state) => state.currentSongID);
  const action = useCurrentSongStore((state) => state.action);
  const setAction = useCurrentSongStore((state) => state.setAction);
  const isLoading = useCurrentSongStore((state) => state.isLoading);

  return (
    <div
      onClick={() => handleClick()}
      onMouseEnter={() => setIsHover(true)}
      onMouseLeave={() => setIsHover(false)}
      onMouseOver={() => setHover(theme ? theme : "#404040")}
      onMouseOut={() => setHover("#404040")}
      className="flex flex-col w-full h-full items-center space-y-2 relative group hover:bg-white/8 cursor-pointer transition-all rounded-2xl md:p-3 p-2"
    >
      <div className="relative w-full aspect-square">
        {cover ? (
          <Image
            src={cover}
            alt={title}
            unoptimized
            fill
            priority
            sizes="(max-width: 640px) 45vw, (max-width: 768px) 30vw, (max-width: 1024px) 23vw, 18vw"
            className={`${type === "profile" ? "rounded-full" : "rounded-lg"
              } object-cover`}
          />
        ) : (
          <Skeleton className="w-full h-full rounded-lg" />
        )}
        {(isLoading && songs.some((song) => song.id.toString() === currentSongID.url)) ? (
          <div className="flex items-center justify-center bottom-4 right-4 shadow-[0_0_20px_0_rgba(0,0,0,0.5)] shadow-black/50 absolute size-[3rem] bg-white rounded-full">
            <LoaderCircle className="text-black animate-spin stroke-3 stroke-black" size={25} />
          </div>
        ) : (
          <button onClick={(e) => {
            e.stopPropagation();
            if (type !== "profile") {
              if (songs.some((song) => song.id.toString() === currentSongID.url)) {
                if (action === "Play") {
                  setAction("Pause");
                } else {
                  setAction("Play");
                }
              } else {
                setAction("Play");
                setCurrentSongID(songs[0].id.toString(),true);
              }
            }
          }} className={`bg-white rounded-full cursor-pointer shadow-[0_0_20px_0_rgba(0,0,0,0.5)] shadow-black/50 size-[3rem] absolute bottom-4 right-4 transition-all flex items-center justify-center ${songs.some((song) => song.id.toString() === currentSongID.url) ? ' translate-y-0 ' : 'group-hover:translate-y-0 translate-y-4 opacity-0 group-hover:opacity-100'}`}>
            {songs.some((song) => song.id.toString() === currentSongID.url) ? (
              action === "Play" ? (
                isHover ?
                  <Pause className="text-black" fill="black" size={20} />
                  : <PlayAnimation isPlaying={true} />
              ) : (
                <Play className="text-black" fill="black" size={20} />
              )
            ) : (
              <Play className="text-black" fill="black" size={20} />
            )}
          </button>
        )}
      </div>
      <div className="w-full flex flex-col justify-start items-start">
        {title ? (
          <h1 className="text-base sm:text-lg md:text-xl lg:text-2xl font-semibold truncate w-full">
            {title}
          </h1>
        ) : (
          <Skeleton className="w-1/2 mb-2 h-[24px]" />
        )}
        {type !== "profile" &&
          (artist ? (
            <p
              onClick={(e) => {
                e.stopPropagation();
                router.push(`/profile/${artistID}`);
              }}
              className="text-white/50 text-xs sm:text-sm truncate w-min cursor-pointer group-hover:text-white transition-colors font-medium hover:underline"
            >
              {artist}
            </p>
          ) : (
            <Skeleton className="w-1/2 h-[20px]" />
          ))}
        {type ? (
          <p className="text-white/50 md:block hidden text-xs sm:text-sm w-max cursor-pointer group-hover:text-white transition-colors font-medium">
            {type.slice(0, 1).toUpperCase() + type.slice(1)}
          </p>
        ) : (
          <Skeleton className="w-1/2 h-[20px]" />
        )}
      </div>
    </div>
  );
}