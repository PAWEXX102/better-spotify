from rest_framework import filters, viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from django.db.models import Q, F
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.shortcuts import render


from .filters import ArtistFilter, AlbumFilter, SongFilter
from .utils import get_top_songs_last_month, create_collage, get_image_url, upload_image
from .models import CustomUser, Album, PlaylistSong, Song, CurrentPlayback, SongPlayback, Playlist, LibraryItem, Library, PlaybackHistory

from .serializers import (ArtistSerializer, AlbumSerializer, SongSerializer, 
                          CurrentPlaybackSerializer, PlaybackActionSerializer, UserPlaybackHistorySerializer, 
                          PlaylistSerializer,
                          LibraryItemSerializer, LibrarySerializer,
                          PlaybackHistorySerializer
                          )

from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils.text import slugify


from collections import defaultdict
import os


# Create your views here.




def testIMG(request):
    if request.method == 'POST':
        image_file = request.FILES['image']
        filename = image_file.name
        upload_image(image_file, filename)
        image_url = get_image_url(filename)
        return render(request, 'result.html', {'image_url': image_url})
    return render(request, 'upload.html')

BASE_URL = 'http://127.0.0.1:8000'

@extend_schema(
    parameters=[
        OpenApiParameter('album_type', type=str, description='Filters by album type (album, single, ep) in specific artist'),
    ]
)
class ArtistViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.prefetch_related('albums')
    serializer_class = ArtistSerializer
    permission_classes = [AllowAny,]
    filterset_class = ArtistFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['username', 'albums__title']
    ordering_fields = ['username', 'albums__title']
    http_method_names = ['get', 'put', 'patch', 'head', 'options']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['many'] = self.action == 'list'
        return context
        
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = serializer.instance

        if instance.image:
            file_data = instance.image
            filename = f"artists/{slugify(instance.username)}_{instance.id}{os.path.splitext(file_data.name)[1]}"
            try:
                upload_image(file_data, filename)
            except Exception as e:
                print(f"Upload failed: {e}")

        return Response(serializer.data, status=status.HTTP_200_OK)

class AlbumViewSet(viewsets.ModelViewSet):
    queryset = Album.objects.prefetch_related('artist', 'songs')
    serializer_class = AlbumSerializer
    permission_classes = [AllowAny,]
    filterset_class = AlbumFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'artist__username', 'release_date']
    ordering_fields = ['title', 'artist__username', 'release_date']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance

        
        if instance.image:
            file_data = instance.image
            filename = f"albums/{slugify(instance.title)}_{instance.id}{os.path.splitext(file_data.name)[1]}"
            # filename = f"albums/{instance.title}{instance.id}"
            try:
                upload_image(file_data, filename)
            except Exception as e:
                print(f"Upload failed: {e}")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = serializer.instance

        if instance.image:
            file_data = instance.image
            filename = f"albums/{slugify(instance.title)}_{instance.id}{os.path.splitext(file_data.name)[1]}"
            try:
                upload_image(file_data, filename)
            except Exception as e:
                print(f"Upload failed: {e}")

        return Response(serializer.data, status=status.HTTP_200_OK)
    
class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    permission_classes = [AllowAny,]
    filterset_class = SongFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'album__title', 'album__artist__username', 'album__release_date']
    ordering_fields = ['title', 'album__title', 'album__artist__username', 'album__release_date']

class SmallResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_query_param = 'page'

@extend_schema(
    parameters=[
        OpenApiParameter('q', type=str, description='Search query'),
    ]
)
class SearchView(APIView):
    permission_classes = [AllowAny,]
    
    @extend_schema(request=None, responses=None)
    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({"results": []})

        paginator = SmallResultsSetPagination()

        # songs = Song.objects.filter(
        #     Q(title__icontains=query) |
        #     Q(album__title__icontains=query) |
        #     Q(album__artist__name__icontains=query)
        # )
        songs = Song.objects.annotate(
            similarity=Greatest(
                TrigramSimilarity('title', query),
                TrigramSimilarity('title', query.lower()),
                TrigramSimilarity('album__title', query),
                TrigramSimilarity('album__title', query.lower()),
                
                TrigramSimilarity('album__artist__username', query),
                TrigramSimilarity('album__artist__username', query.lower())
            )
        ).filter(
            Q(title__icontains=query) |
            Q(album__title__icontains=query) |
            Q(album__artist__username__icontains=query) | Q(similarity__gt=0.2)
        ).order_by('-similarity')

        # albums = Album.objects.filter(
        #     Q(title__icontains=query) |
        #     Q(artist__name__icontains=query)
        # )
        albums = Album.objects.annotate(
            similarity=Greatest(
                TrigramSimilarity('title', query),
                TrigramSimilarity('title', query.lower()),
                TrigramSimilarity('artist__username', query),
                TrigramSimilarity('artist__username', query.lower())
            )
        ).filter(
            Q(title__icontains=query) |
            Q(artist__username__icontains=query) | Q(similarity__gt=0.2)
        ).order_by('-similarity')


        # artists = Artist.objects.filter(name__icontains=query)
        artists = CustomUser.objects.annotate(
            similarity=Greatest(
                TrigramSimilarity('username', query),
                TrigramSimilarity('username', query.lower())
            )
        ).filter(
            Q(username__icontains=query) | Q(similarity__gt=0.2)
        ).order_by('-similarity')


        playlists = Playlist.objects.annotate(
            similarity=Greatest(
                TrigramSimilarity('name', query),
                TrigramSimilarity('name', query.lower()),
                TrigramSimilarity('user__username', query),
                TrigramSimilarity('user__username', query.lower())
            )
        ).filter(
            (Q(user__username__icontains=query) |
            Q(name__icontains=query) | Q(similarity__gt=0.2)) & Q(is_public=True)
        ).order_by('-similarity')

        combined_results = list(songs) + list(albums) + list(artists) + list(playlists)
        combined_results = sorted(combined_results, key=lambda x: self.get_relevance(x, query), reverse=False)
        combined_results.reverse()

        paginated_results = paginator.paginate_queryset(combined_results, request)

        results = []
        for obj in paginated_results:
            if isinstance(obj, Song):
                result_data = SongSerializer(obj, context={'request': request}).data
                result_data['data_type'] = 'song'
                result_data['cover'] = BASE_URL + obj.album.image.url if obj.album.image else None
                results.append(result_data)
            elif isinstance(obj, Album):
                result_data = AlbumSerializer(obj, context={'request': request}).data
                result_data['data_type'] = 'album'
                results.append(result_data)
                # result_data.pop('songs', None)
            elif isinstance(obj, CustomUser):
                result_data = ArtistSerializer(obj, context={'request': request}).data
                result_data['data_type'] = 'artist'
                results.append(result_data)
                result_data.pop('albums', None)
            elif isinstance(obj, Playlist):
                result_data = PlaylistSerializer(obj, context={'request': request}).data
                result_data['data_type'] = 'playlist'
                results.append(result_data)
                result_data.pop('songs', None)

        return paginator.get_paginated_response(results)

    def get_relevance(self, obj, query):
        if isinstance(obj, Song):
            return obj.title.lower().count(query.lower()) + obj.album.title.lower().count(query.lower())
        elif isinstance(obj, Album):
            return obj.title.lower().count(query.lower()) + obj.artist.username.lower().count(query.lower())
        elif isinstance(obj, CustomUser):
            return obj.username.lower().count(query.lower())
        elif isinstance(obj, Playlist):
            return obj.name.lower().count(query.lower()) + obj.user.username.lower().count(query.lower())
        return 0
    

@extend_schema(
    parameters=[
        OpenApiParameter('action', type=str, description='Action to perform (play, pause, resume, reset, seek)'),
        OpenApiParameter('song_id', type=int, description='ID of the song to play or reset'),
        OpenApiParameter('progress_seconds', type=int, description='Used for seek action, seconds to seek to'),
    ]
)
class PlaybackControlAPIView(APIView):
    permission_classes = [IsAuthenticated,]
    serializer_class = PlaybackActionSerializer

    def post(self, request):
        serializer = PlaybackActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        song_id = serializer.validated_data.get('song_id')
        progress_seconds = serializer.validated_data.get('progress_seconds', None)

        current_playback = CurrentPlayback.objects.get(user=request.user)

        if action == 'play':
            if not song_id:
                return Response({"error": "song_id is required"}, status=400)
            song = Song.objects.get(id=song_id)
            current_playback.play(song)
            return Response({"status": "Played"})
        elif action == 'pause':
            current_playback.pause()
            return Response({"status": "Paused"})
        elif action == 'resume':
            current_playback.resume()
            return Response({"status": "Playing"})
        elif action == 'reset':
            if not song_id:
                current_playback.reset()
            else:
                song = Song.objects.get(id=song_id)
                current_playback.reset(song)
            return Response({"status": "Stopped"})
        elif action == 'seek':
            if progress_seconds is None:
                return Response({"error": "progress_seconds is required"}, status=400)
            current_playback.seek_to(progress_seconds)
            return Response({"status": "Seeked to {}".format(progress_seconds)})

        
    def get(self, request):
        current_playback = CurrentPlayback.objects.get(user=request.user)
        if current_playback.song:
            data = CurrentPlaybackSerializer(current_playback).data
            if current_playback.is_paused:
                return Response({"data": data, "status": "Paused"})
            else:
                return Response({"data": data, "status": "Playing"})
        return Response({"status": "Not playing any song"})
    


class UserPlaybackHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    @extend_schema(
        request=None,
        responses={
            200: UserPlaybackHistorySerializer(many=True),
        }
    )
    def get(self, request):
        user = request.user
        last_month = timezone.now() - timezone.timedelta(days=30)
        playback_history = SongPlayback.objects.filter(user=user, played_at__gte=last_month).select_related('user', 'song').order_by('-played_at')
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        result_page = paginator.paginate_queryset(playback_history, request)

        serializer = UserPlaybackHistorySerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class TopSongsAPIView(APIView):
    permission_classes = [AllowAny,]

    @extend_schema(
        request=None,
        responses={
            200: {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'genre': {'type': 'string'},
                        'cover': {'type': 'string', 'format': 'uri'},
                        'songs': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'title': {'type': 'string'},
                                    'artist': {'type': 'integer'},
                                    'album': {'type': 'integer'},
                                    'duration': {'type': 'integer'},
                                    'play_count': {'type': 'integer'}
                                },
                            }
                        }
                    },
                }
            }
        }
    )
    def get(self, request, genre=None):
        top_songs = list(get_top_songs_last_month(10, genre))
        result = defaultdict(list)

        for entry in top_songs:
            genre_label = entry['genre_label']
            result[genre_label].append({
                'song': entry['song__id'],
                'play_count': entry['play_count']
            })

        grouped_result = dict(result)
        print('Grouped Result: ', grouped_result)


        data = []
        for genre_items, value in grouped_result.items():
            songs_data = []
            for song in value:
                song_obj = SongSerializer(Song.objects.get(id=song['song']), context={'request': request}).data
                song_obj.pop('lyrics')
                song_obj.pop('genre')

                # song_obj.pop('plays')

                songs_data.append(song_obj)

            detail_data = {}
            
            detail_data['genre'] = genre_items
            detail_data['cover'] = BASE_URL + CustomUser.objects.get(id=songs_data[0]['artist']).get_image_url if songs_data[0]['artist'] else ""
            if genre:
                detail_data['songs'] = songs_data
            data.append(detail_data)

        return Response(data)
    

class UserPlaylistViewSet(viewsets.ModelViewSet):
    queryset = Playlist.objects.all()
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticated,]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'id']
    ordering_fields = ['name', 'created_at']


    def get_queryset(self):
        user = self.request.user
        # try:
        #     songs_order = self.request.query_params['songs_order']
            
        #     order = ''
        #     if songs_order == 'title':
        #         order = 'songs__title'
        #     elif songs_order == '-title':
        #         order = '-songs__title'
        #     elif songs_order == 'songs_order':
        #         order = 'songs__order'
        #     elif songs_order == '-songs_order':
        #         order = '-songs__order'

        #     return Playlist.objects.filter(user=user)
        # except:
        return Playlist.objects.filter(user=user)
        
    
    def create(self, request):
        serializer = PlaylistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save(user=request.user)
        library = Library.objects.get(user=request.user)
        library_item = LibraryItem.objects.create(
            library=library,
            content_type=ContentType.objects.get_for_model(Playlist),
            object_id=playlist.id
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    



class ModifyPlaylistAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    @extend_schema(
        parameters=[
            OpenApiParameter('playlist_id', type=int, description='ID of the playlist to modify'),
            OpenApiParameter('song_ids', type=int, description='Comma-separated list of song IDs to add or remove'),
            OpenApiParameter('action', type=str, description='Action to perform (add or remove)')
        ],
        request=None,
        responses={
            200: {
                'status': {'type': 'string'},
            },
        }
    )
    def post(self, request):
        playlist_id = request.data.get('playlist_id', None)
        if not playlist_id:
            return Response({"error": "playlist_id is required"}, status=400)
        playlist = Playlist.objects.get(id=playlist_id, user=request.user)
        song_ids = request.data.get('song_ids', [])
        action = request.data.get('action', 'add')


        if action == 'add':
            playlist_song_length = PlaylistSong.objects.filter(playlist=playlist).count()
            for idx, song_id in enumerate(song_ids):
                playlist_song, created = PlaylistSong.objects.get_or_create(
                    playlist=playlist,
                    song_id=song_id,
                    order=idx+playlist_song_length,
                )
                playlist_song.save()


        elif action == 'remove':
            for song_id in song_ids:
                try:
                    song = PlaylistSong.objects.get(playlist=playlist, song_id=song_id)
                    removed_order = song.order
                    song.delete()

                    PlaylistSong.objects.filter(
                        playlist=playlist,
                        order__gt=removed_order
                    ).update(order=F('order') - 1)

                except PlaylistSong.DoesNotExist:
                    continue



        images = []
        for song in playlist.songs.all():
            if song.album.image:
                images.append(song.album.image.name)

        if images:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'playlists'), exist_ok=True)

            relative_path = os.path.join('playlists', f'playlist{playlist.id}.png')
            save_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            collage = create_collage(images, save_path, size=(800, 800))

            playlist.image = relative_path
            playlist.save()

        return Response({"status": "success", "playlist": PlaylistSerializer(playlist, context={}).data})
    



class LibraryAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        library = Library.objects.get(user=request.user)
        serializer = LibrarySerializer(library, context={'request': request})
        return Response(serializer.data)



@extend_schema(
    parameters=[
        OpenApiParameter('action', type=str, description="Action to perform ('add' or 'remove')"),
        OpenApiParameter('object_type', type=str, description="Type of object ('song', 'album', 'customuser')"),
        OpenApiParameter('id', type=int, description="ID of the object to add or remove"),
    ],
    request=None,
    responses={
        200: {
            'status': {'type': 'string'},
        },
    }
)
class ModifyLibraryAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        library = Library.objects.get(user=request.user)
        action = request.data.get('action', 'add')
        obj_id = request.data.get('id', None)
        object_type = request.data.get('object_type', None)
        
        if object_type not in ['song', 'album', 'playlist', 'customuser']:
                return Response({"error": "object_type must be either 'song', 'album' or 'customuser'"}, status=400)

        model_map = {
                'song': Song,
                'album': Album,
                'playlist': Playlist,
                'customuser': CustomUser
            }
        model = model_map.get(object_type)



        if action == 'add':
            library_item, created = LibraryItem.objects.get_or_create(
                library=library,
                content_type=ContentType.objects.get_for_model(model),
                object_id=obj_id
            )
            library_item.save()
            if object_type == 'playlist':
                playlist = library_item.content_object
                playlist.savings += 1
                playlist.save()


        elif action == 'remove':
            try:
                song = LibraryItem.objects.get(library=library, object_id=obj_id, content_type=ContentType.objects.get_for_model(model))
                if object_type == 'playlist':
                    playlist = song.content_object
                    playlist.savings -= 1
                song.delete()
            except LibraryItem.DoesNotExist:
                print('LibraryItem does not exist, id: ', obj_id)
                pass

        return Response({"status": "success"})
    


@extend_schema(
    parameters=[
        OpenApiParameter('user_id', type=int, description='ID of the artist to follow/unfollow'),
    ],
    request=None,
    responses={
        200: {
            'status': {'type': 'string'},
        },
    }
)
class ToggleFollowAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        user_id = request.data.get('user_id', None)

        if not user_id:
            return Response({"error": "user_id are required"}, status=400)

        try:
            artist = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "Artist not found"}, status=404)

        request.user.follow(artist)
        if artist in request.user.followed_artists.all():
            return Response({"status": "Following"})
        else:
            return Response({"status": "Unfollowed"})
        


class PlaybackHistoryViewSet(viewsets.ModelViewSet):
    queryset = PlaybackHistory.objects.all()
    serializer_class = PlaybackHistorySerializer
    permission_classes = [IsAuthenticated,]

    def get_queryset(self):
        user = self.request.user
        return PlaybackHistory.objects.filter(user=user)