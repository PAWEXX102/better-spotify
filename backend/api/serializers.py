from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.templatetags.static import static
from mutagen.mp3 import MP3
import datetime
import os
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, F
from django.conf import settings
from .utils import get_dominant_color, create_collage
from .models import CustomUser, Album, Song, CurrentPlayback, SongPlayback, Playlist, PlaylistSong, Library, LibraryItem

BASE_URL = "http://127.0.0.1:8000"

class SongSerializer(serializers.ModelSerializer):
    artist = serializers.PrimaryKeyRelatedField(read_only=True, source='album.artist.id')
    plays_test = serializers.SerializerMethodField()
    class Meta:
        model = Song
        fields = [
            'id', 'album', 'artist', 'title', 'duration', 
            'file', 'lyrics', 'track_number', 'plays', 'genre',
            'is_indecent', 'featured_artists', 'plays_test'
        ]
        extra_kwargs = {
            'duration': {'read_only': True},
        }

    @extend_schema_field(serializers.IntegerField)
    def get_plays_test(self, obj):
        songs = SongPlayback.objects.filter(song=obj).count()
        return songs

    def __init__(self, *args, **kwargs):
        nested = kwargs.pop('nested', False)
        self.playlist = kwargs.pop('playlist', False)

        super().__init__(*args, **kwargs)
        if nested:
            # self.fields.pop('album')
            self.fields.pop('lyrics')
            self.fields.pop('file')
            self.fields.pop('genre')


    def validate_lyrics(self, value):
        if value in (None, '', []):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Lyrics must be a valid JSON object.")
        return value


    def create(self, validated_data):
        featured_artists = validated_data.pop('featured_artists', [])

        lyrics = validated_data.get('lyrics')
        if not isinstance(lyrics, dict):
            validated_data['lyrics'] = {}

        try:
            artist_to_remove = next(artist for artist in featured_artists if validated_data['album'].artist.id == artist.id)
            featured_artists.remove(artist_to_remove)
        except StopIteration:
            pass

        song = Song.objects.create(duration="0:00", **validated_data)
        song.featured_artists.set(featured_artists)
        
        audio = MP3(song.file.path)
        
        song_duration = datetime.timedelta(seconds=round(audio.info.length))
        song.duration = song_duration
        song.save()

        return song
    
    def update(self, instance, validated_data):
        featured_artists = validated_data.pop('featured_artists', None)
        file = validated_data.get('file', None)
        instance.file = file if file else instance.file

        
        lyrics = validated_data.get('lyrics')
        if not isinstance(lyrics, dict):
            validated_data['lyrics'] = {}

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if featured_artists is not None:
            artist_to_remove = next((artist for artist in featured_artists if instance.album.artist.id == artist.id), None)

            if artist_to_remove:
                featured_artists.remove(artist_to_remove)
            instance.featured_artists.set(featured_artists)

        if file:
            instance.save(update_fields=['file'])

            if os.path.exists(instance.file.path):
                audio = MP3(instance.file.path)
                song_duration = datetime.timedelta(seconds=round(audio.info.length))
                instance.duration = song_duration

        instance.save()
        return instance
    

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # if self.playlist:
        representation['cover'] = BASE_URL + instance.album.image.url if instance.album.image else None
        return representation






class AlbumSerializer(serializers.ModelSerializer):
    songs = serializers.SerializerMethodField()
    album_duration = serializers.SerializerMethodField()
    total_plays = serializers.SerializerMethodField()
    # theme = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = [
            'id', 'title', 'album_type', 'artist', 'image', 
            'release_date', 'album_duration', 'theme',
            'total_plays', 'songs'
        ]
        extra_kwargs = {
            'theme': {'required': False},
        }


    def __init__(self, *args, **kwargs):
        nested = kwargs.pop('nested', False)
        super().__init__(*args, **kwargs)
        if nested:
            self.fields.pop('artist')
            self.fields.pop('songs')
    

    @extend_schema_field(serializers.ListField)
    def get_songs(self, obj):
        return SongSerializer(obj.songs.order_by('track_number'), many=True, nested=True, context=self.context, required=False).data
    

    @extend_schema_field(serializers.DurationField)
    def get_album_duration(self, obj):
        total_time = datetime.timedelta(0)
        for song in obj.songs.all():
            total_time += song.duration
        return str(total_time)

    @extend_schema_field(serializers.IntegerField)
    def get_total_plays(self, obj):
        return sum(song.plays for song in obj.songs.all())


    def create(self, validated_data):
        try:
            songs_data = validated_data.pop('songs')
        except KeyError:
            songs_data = []
        album = Album.objects.create(**validated_data)
        for song_data in songs_data:
            Song.objects.create(album=album, **song_data)

        if album.theme == "" and album.image:
            image_path = album.image.path
            if os.path.exists(image_path):
                dominant_color = get_dominant_color(image_path)
                album.theme = dominant_color
                album.save()
        return album
    
    
    def update(self, instance, validated_data):
        songs_data = validated_data.pop('songs', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if songs_data is not None:
            for song_data in songs_data:
                song_id = song_data.get('id', None)
                if song_id:
                    song = Song.objects.get(id=song_id, album=instance)
                    for key, value in song_data.items():
                        setattr(song, key, value)
                    song.save()
                else:
                    Song.objects.create(album=instance, **song_data)

        if instance.theme == "" and instance.image:
            image_path = instance.image.path
            if os.path.exists(image_path):
                dominant_color = get_dominant_color(image_path)
                instance.theme = dominant_color
                instance.save()

        return instance
    






class ArtistSerializer(serializers.ModelSerializer):
    top_songs = serializers.SerializerMethodField()
    number_of_listeners = serializers.SerializerMethodField()
    number_of_popularity = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'image', 'type', 'number_of_listeners', 'number_of_popularity', 'number_of_followers', 'albums', 'top_songs']

    def __init__(self, *args, **kwargs):
        self.nested = kwargs.pop('nested', False)
        super().__init__(*args, **kwargs)

        if self.context.get('many', False):
            self.fields.pop('top_songs')

        if self.nested:
            self.fields.pop('albums')
            self.fields.pop('number_of_listeners')
            self.fields.pop('number_of_popularity')
            self.fields.pop('number_of_followers')
            self.fields.pop('type')
            self.fields.pop('top_songs')

        


    @extend_schema_field(serializers.IntegerField)
    def get_number_of_listeners(self, obj):
        last_month = timezone.now() - timedelta(days=30)
        return SongPlayback.objects.filter(
            song__album__artist=obj,
            played_at__gte=last_month
        ).aggregate(Count('user', distinct=True))['user__count']
    

    @extend_schema_field(serializers.IntegerField)
    def get_number_of_popularity(self, obj):
        artists = CustomUser.objects.filter(type='artist')
        popularity = {}
        for artist in artists:
            popularity[artist.id] = self.get_number_of_listeners(artist)

        popularity = dict(sorted(popularity.items(), key=lambda item: item[1], reverse=True))


        number_popularity = 0
        for artist in popularity.keys():
            number_popularity += 1
            if artist == obj.id:
                break
        
        return number_popularity
    
    @extend_schema_field(serializers.ListField)
    def get_top_songs(self, obj):
        limit = 10
        last_month = timezone.now() - timedelta(days=30)
    
        songs_ids = SongPlayback.objects.filter(
            song__album__artist=obj,
            played_at__gte=last_month
        ).values(
            'song'
        ).annotate(
            play_count=Count('id')
        ).order_by('-play_count')[:limit]

        songs = []
        for song in songs_ids:
            song = Song.objects.get(id=song['song'])
            songs.append(song)


        return SongSerializer(songs, many=True, nested=True, context=self.context).data

    
    def to_representation(self, instance):
        album_type = None
        if 'request' in self.context and hasattr(self.context['request'], 'query_params'):
            album_type = self.context['request'].query_params.get('album_type', None)

        if album_type:
            albums = instance.albums.filter(album_type=album_type).order_by('-release_date')
        else:
            albums = instance.albums.all().order_by('-release_date')

        representation = super().to_representation(instance)
        
        if instance.type != 'artist':# or self.context.get('many', False):
            representation.pop('albums', None)

        if instance.image == '':
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(static('default.jpg'))
            else:
                representation['image'] = static('default.jpg')


        if instance.type == 'listener':
            representation.pop('number_of_listeners')
            representation.pop('number_of_popularity')


        if request := self.context.get('request'):
            try:
                if instance in request.user.followed_artists.all():
                    representation['is_followed'] = True
                else:
                    representation['is_followed'] = False

                if instance == request.user:
                    representation.pop('is_followed', None)
            except AttributeError:
                representation['is_followed'] = False    


        view = self.context.get('view')
        if view and getattr(view, 'action', None) == 'list':
            pass
        elif view and getattr(view, 'action', None) == 'retrieve':
            representation['albums'] = AlbumSerializer(albums, many=True, nested=True, context=self.context).data
        
        if self.nested:
            representation.pop('albums', None)
        
        return representation
    





class PlaybackActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['play', 'pause', 'resume', 'reset'])
    song_id = serializers.IntegerField(required=False)
    progress_seconds = serializers.IntegerField(required=False)




class CurrentPlaybackSerializer(serializers.ModelSerializer):
    song = SongSerializer(nested=True)
    class Meta:
        model = CurrentPlayback
        fields = [
            'song', 'song_id', 
            'started_at', 'progress_seconds', 'paused_at', 
            'is_paused'
        ]



class UserPlaybackHistorySerializer(serializers.Serializer):
    song = SongSerializer(nested=True)
    played_at = serializers.DateTimeField()
        




class PlaylistSerializer(serializers.ModelSerializer):
    # songs = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    songs = serializers.PrimaryKeyRelatedField(queryset=Song.objects.all(), many=True, write_only=True, required=False)
    theme = serializers.SerializerMethodField()
    playlist_duration = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ['id', 'user', 'name', 'description', 'image', 'is_public', 'has_image', 'theme', 'playlist_duration', 'savings', 'songs',]
        extra_kwargs = {
            'savings': {'read_only': True},
        }


    def __init__(self, instance=None, *args, **kwargs):
        self.nested = kwargs.pop('nested', False)
        super().__init__(instance, *args, **kwargs)

        if self.nested:
            self.fields.pop('songs')


    @extend_schema_field(serializers.DurationField)
    def get_playlist_duration(self, obj):
        playlist_songs = PlaylistSong.objects.filter(playlist=obj).order_by('order')
        songs = [playlist_song.song for playlist_song in playlist_songs]
        total_time = datetime.timedelta(0)
        for song in songs:
            total_time += song.duration
        return str(total_time)

    # @extend_schema_field(serializers.ListField)
    # def get_songs(self, obj):
    #     playlist_songs = PlaylistSong.objects.filter(playlist=obj).order_by('order')
    #     songs = [playlist_song.song for playlist_song in playlist_songs]
    #     return SongSerializer(songs, many=True, nested=True).data

    @extend_schema_field(serializers.CharField)
    def get_theme(self, obj):
        return get_dominant_color(obj.image.path, 'RGBA') if obj.image else None


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        playlist_songs = PlaylistSong.objects.filter(playlist=instance).order_by('order')
        songs = [playlist_song.song for playlist_song in playlist_songs]
        
        representation['songs'] = SongSerializer(songs, many=True, nested=True, playlist=True).data
        if self.nested:
            representation.pop('songs', None)

        return representation
    

    def create(self, validated_data):
        songs_order = validated_data.pop('songs', None)
        playlist = Playlist.objects.create(**validated_data)

        if songs_order:
            for idx, song_id in enumerate(songs_order):
                playlist_song, created = PlaylistSong.objects.get_or_create(
                    playlist=playlist,
                    song=song_id,
                    order=idx,
                )
                playlist_song.save()

        if playlist.has_image:
            return playlist
        
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

        return playlist
    

    def update(self, instance, validated_data):
        songs_order = validated_data.pop('songs', None)
        instance = super().update(instance, validated_data)

        if songs_order:
            existing_playlist_songs = PlaylistSong.objects.filter(playlist=instance)

            for playlist_song in existing_playlist_songs:
                    playlist_song.delete()

            for idx, song_id in enumerate(songs_order):
                playlist_song, created = PlaylistSong.objects.get_or_create(
                    playlist=instance,
                    song=song_id,
                    order=idx,
                )
                playlist_song.save()


        if instance.has_image:
            return instance

        images = []
        for song in instance.songs.all():
            if song.album.image:
                images.append(song.album.image.name)

        if images:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'playlists'), exist_ok=True)

            relative_path = os.path.join('playlists', f'playlist{instance.id}.png')
            save_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            collage = create_collage(images, save_path, size=(800, 800))

            instance.image = relative_path
            instance.save()

        return instance
    




class LibraryItemSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source='content_type.model', read_only=True)
    library_obj = serializers.SerializerMethodField()

    class Meta:
        model = LibraryItem
        fields = ['id', 'content_type', 'library_obj']


    @extend_schema_field(serializers.DictField)
    def get_library_obj(self, obj):
        content_type = obj.content_type.model_class()
        if content_type:
            try:
                library_object = content_type.objects.get(id=obj.object_id)
                if isinstance(library_object, Song):
                    return SongSerializer(library_object, nested=True, context=self.context).data
                elif isinstance(library_object, Playlist):
                    return PlaylistSerializer(library_object, nested=True, context=self.context).data
                elif isinstance(library_object, Album):
                    return AlbumSerializer(library_object, nested=True, context=self.context).data
                elif isinstance(library_object, CustomUser):
                    return ArtistSerializer(library_object, nested=True, context=self.context).data
            except content_type.DoesNotExist:
                return None
        return None




class LibrarySerializer(serializers.ModelSerializer):
    items = LibraryItemSerializer(many=True, read_only=True)
    class Meta:
        model = Library
        fields = ['id', 'user', 'items']