using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace AutoClipStudio.WPF.Controls;

/// <summary>
/// Custom control for displaying a clip card in results.
/// </summary>
public class ClipCard : Control
{
    static ClipCard()
    {
        DefaultStyleKeyProperty.OverrideMetadata(typeof(ClipCard), new FrameworkPropertyMetadata(typeof(ClipCard)));
    }

    #region Dependency Properties

    public static readonly DependencyProperty ClipProperty =
        DependencyProperty.Register(nameof(Clip), typeof(object), typeof(ClipCard), new PropertyMetadata(null));

    public object Clip
    {
        get => GetValue(ClipProperty);
        set => SetValue(ClipProperty, value);
    }

    public static readonly DependencyProperty IdProperty =
        DependencyProperty.Register(nameof(Id), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string Id
    {
        get => (string)GetValue(IdProperty);
        set => SetValue(IdProperty, value);
    }

    public static readonly DependencyProperty HookProperty =
        DependencyProperty.Register(nameof(Hook), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string Hook
    {
        get => (string)GetValue(HookProperty);
        set => SetValue(HookProperty, value);
    }

    public static readonly DependencyProperty DevelopmentProperty =
        DependencyProperty.Register(nameof(Development), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string Development
    {
        get => (string)GetValue(DevelopmentProperty);
        set => SetValue(DevelopmentProperty, value);
    }

    public static readonly DependencyProperty ClosingProperty =
        DependencyProperty.Register(nameof(Closing), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string Closing
    {
        get => (string)GetValue(ClosingProperty);
        set => SetValue(ClosingProperty, value);
    }

    public static readonly DependencyProperty ScoreProperty =
        DependencyProperty.Register(nameof(Score), typeof(double), typeof(ClipCard), new PropertyMetadata(0.0));

    public double Score
    {
        get => (double)GetValue(ScoreProperty);
        set => SetValue(ScoreProperty, value);
    }

    public static readonly DependencyProperty ScoreBreakdownProperty =
        DependencyProperty.Register(nameof(ScoreBreakdown), typeof(System.Collections.IDictionary), typeof(ClipCard), new PropertyMetadata(null));

    public System.Collections.IDictionary ScoreBreakdown
    {
        get => (System.Collections.IDictionary)GetValue(ScoreBreakdownProperty);
        set => SetValue(ScoreBreakdownProperty, value);
    }

    public static readonly DependencyProperty ScoreExplanationProperty =
        DependencyProperty.Register(nameof(ScoreExplanation), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string ScoreExplanation
    {
        get => (string)GetValue(ScoreExplanationProperty);
        set => SetValue(ScoreExplanationProperty, value);
    }

    public static readonly DependencyProperty SocialCopyProperty =
        DependencyProperty.Register(nameof(SocialCopy), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string SocialCopy
    {
        get => (string)GetValue(SocialCopyProperty);
        set => SetValue(SocialCopyProperty, value);
    }

    public static readonly DependencyProperty HashtagsProperty =
        DependencyProperty.Register(nameof(Hashtags), typeof(System.Collections.IList), typeof(ClipCard), new PropertyMetadata(null));

    public System.Collections.IList Hashtags
    {
        get => (System.Collections.IList)GetValue(HashtagsProperty);
        set => SetValue(HashtagsProperty, value);
    }

    public static readonly DependencyProperty LayoutProperty =
        DependencyProperty.Register(nameof(Layout), typeof(string), typeof(ClipCard), new PropertyMetadata("solo_podcast"));

    public string Layout
    {
        get => (string)GetValue(LayoutProperty);
        set => SetValue(LayoutProperty, value);
    }

    public static readonly DependencyProperty BackgroundAssetProperty =
        DependencyProperty.Register(nameof(BackgroundAsset), typeof(string), typeof(ClipCard), new PropertyMetadata(null));

    public string? BackgroundAsset
    {
        get => (string?)GetValue(BackgroundAssetProperty);
        set => SetValue(BackgroundAssetProperty, value);
    }

    public static readonly DependencyProperty SubtitlePathProperty =
        DependencyProperty.Register(nameof(SubtitlePath), typeof(string), typeof(ClipCard), new PropertyMetadata(null));

    public string? SubtitlePath
    {
        get => (string?)GetValue(SubtitlePathProperty);
        set => SetValue(SubtitlePathProperty, value);
    }

    public static readonly DependencyProperty VideoPathProperty =
        DependencyProperty.Register(nameof(VideoPath), typeof(string), typeof(ClipCard), new PropertyMetadata(null));

    public string? VideoPath
    {
        get => (string?)GetValue(VideoPathProperty);
        set => SetValue(VideoPathProperty, value);
    }

    public static readonly DependencyProperty PreviewImageProperty =
        DependencyProperty.Register(nameof(PreviewImage), typeof(string), typeof(ClipCard), new PropertyMetadata(null));

    public string? PreviewImage
    {
        get => (string?)GetValue(PreviewImageProperty);
        set => SetValue(PreviewImageProperty, value);
    }

    public static readonly DependencyProperty DurationTextProperty =
        DependencyProperty.Register(nameof(DurationText), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string DurationText
    {
        get => (string)GetValue(DurationTextProperty);
        set => SetValue(DurationTextProperty, value);
    }

    public static readonly DependencyProperty TimecodeRangeProperty =
        DependencyProperty.Register(nameof(TimecodeRange), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string TimecodeRange
    {
        get => (string)GetValue(TimecodeRangeProperty);
        set => SetValue(TimecodeRangeProperty, value);
    }

    public static readonly DependencyProperty LayoutDisplayNameProperty =
        DependencyProperty.Register(nameof(LayoutDisplayName), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string LayoutDisplayName
    {
        get => (string)GetValue(LayoutDisplayNameProperty);
        set => SetValue(LayoutDisplayNameProperty, value);
    }

    public static readonly DependencyProperty ScorePercentProperty =
        DependencyProperty.Register(nameof(ScorePercent), typeof(string), typeof(ClipCard), new PropertyMetadata(""));

    public string ScorePercent
    {
        get => (string)GetValue(ScorePercentProperty);
        set => SetValue(ScorePercentProperty, value);
    }

    public static readonly DependencyProperty ScoreColorProperty =
        DependencyProperty.Register(nameof(ScoreColor), typeof(Brush), typeof(ClipCard), new PropertyMetadata(null));

    public Brush ScoreColor
    {
        get => (Brush)GetValue(ScoreColorProperty);
        set => SetValue(ScoreColorProperty, value);
    }

    public static readonly DependencyProperty HasPreviewProperty =
        DependencyProperty.Register(nameof(HasPreview), typeof(bool), typeof(ClipCard), new PropertyMetadata(false));

    public bool HasPreview
    {
        get => (bool)GetValue(HasPreviewProperty);
        set => SetValue(HasPreviewProperty, value);
    }

    public static readonly DependencyProperty HasVideoProperty =
        DependencyProperty.Register(nameof(HasVideo), typeof(bool), typeof(ClipCard), new PropertyMetadata(false));

    public bool HasVideo
    {
        get => (bool)GetValue(HasVideoProperty);
        set => SetValue(HasVideoProperty, value);
    }

    public static readonly DependencyProperty ShowPlayButtonProperty =
        DependencyProperty.Register(nameof(ShowPlayButton), typeof(bool), typeof(ClipCard), new PropertyMetadata(true));

    public bool ShowPlayButton
    {
        get => (bool)GetValue(ShowPlayButtonProperty);
        set => SetValue(ShowPlayButtonProperty, value);
    }

    #endregion

    #region Commands

    public static readonly DependencyProperty PlayCommandProperty =
        DependencyProperty.Register(nameof(PlayCommand), typeof(ICommand), typeof(ClipCard), new PropertyMetadata(null));

    public ICommand PlayCommand
    {
        get => (ICommand)GetValue(PlayCommandProperty);
        set => SetValue(PlayCommandProperty, value);
    }

    public static readonly DependencyProperty CopySocialCopyCommandProperty =
        DependencyProperty.Register(nameof(CopySocialCopyCommand), typeof(ICommand), typeof(ClipCard), new PropertyMetadata(null));

    public ICommand CopySocialCopyCommand
    {
        get => (ICommand)GetValue(CopySocialCopyCommandProperty);
        set => SetValue(CopySocialCopyCommandProperty, value);
    }

    public static readonly DependencyProperty ReviewSubtitlesCommandProperty =
        DependencyProperty.Register(nameof(ReviewSubtitlesCommand), typeof(ICommand), typeof(ClipCard), new PropertyMetadata(null));

    public ICommand ReviewSubtitlesCommand
    {
        get => (ICommand)GetValue(ReviewSubtitlesCommandProperty);
        set => SetValue(ReviewSubtitlesCommandProperty, value);
    }

    public static readonly DependencyProperty ExportCommandProperty =
        DependencyProperty.Register(nameof(ExportCommand), typeof(ICommand), typeof(ClipCard), new PropertyMetadata(null));

    public ICommand ExportCommand
    {
        get => (ICommand)GetValue(ExportCommandProperty);
        set => SetValue(ExportCommandProperty, value);
    }

    public static readonly DependencyProperty ShowScoreDetailsCommandProperty =
        DependencyProperty.Register(nameof(ShowScoreDetailsCommand), typeof(ICommand), typeof(ClipCard), new PropertyMetadata(null));

    public ICommand ShowScoreDetailsCommand
    {
        get => (ICommand)GetValue(ShowScoreDetailsCommandProperty);
        set => SetValue(ShowScoreDetailsCommandProperty, value);
    }

    #endregion
}