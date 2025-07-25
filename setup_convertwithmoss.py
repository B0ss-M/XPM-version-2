#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
ConvertWithMoss Setup Guide
Helps users install Java and test ConvertWithMoss integration
"""

import subprocess
import platform
import os

def check_java_installation():
    """Check if Java is properly installed"""
    
    print("🔍 Checking Java Installation...")
    print("=" * 40)
    
    # Check if java command exists
    try:
        result = subprocess.run(['which', 'java'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            java_path = result.stdout.strip()
            print(f"✅ Java executable found: {java_path}")
            
            # Try to get version
            try:
                version_result = subprocess.run(['java', '-version'], 
                                              capture_output=True, text=True)
                if version_result.returncode == 0:
                    print(f"✅ Java is working properly")
                    print(f"Version info: {version_result.stderr[:200]}...")  # Java version goes to stderr
                    return True
                else:
                    print(f"⚠️  Java found but not working properly")
                    print(f"Error: {version_result.stderr}")
                    return False
                    
            except Exception as e:
                print(f"⚠️  Java found but version check failed: {e}")
                return False
        else:
            print("❌ Java executable not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking for Java: {e}")
        return False

def show_installation_instructions():
    """Show platform-specific Java installation instructions"""
    
    print("\\n📦 Java Installation Instructions")
    print("=" * 40)
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        print("🍎 macOS Installation Options:")
        print("\\n1. 🍺 Using Homebrew (Recommended):")
        print("   brew install openjdk")
        print("   # Then add to your PATH:")
        print("   echo 'export PATH=\"/opt/homebrew/bin:$PATH\"' >> ~/.zshrc")
        print("   source ~/.zshrc")
        
        print("\\n2. 📥 Oracle Java (Official):")
        print("   • Download from: https://www.oracle.com/java/technologies/downloads/")
        print("   • Choose macOS installer (.dmg)")
        print("   • Run installer and follow prompts")
        
        print("\\n3. ☕ OpenJDK (Alternative):")
        print("   • Download from: https://adoptium.net/")
        print("   • Choose macOS package for your chip (Intel/Apple Silicon)")
        
        # Check if Homebrew is available
        try:
            result = subprocess.run(['which', 'brew'], capture_output=True, text=True)
            if result.returncode == 0:
                print("\\n✅ Homebrew detected - you can run: brew install openjdk")
            else:
                print("\\n💡 Consider installing Homebrew first: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        except:
            pass
            
    elif system == "Linux":
        print("🐧 Linux Installation:")
        print("   # Ubuntu/Debian:")
        print("   sudo apt update && sudo apt install openjdk-11-jdk")
        print("   # or")
        print("   sudo apt install default-jdk")
        
        print("   # CentOS/RHEL/Fedora:")
        print("   sudo yum install java-11-openjdk-devel")
        print("   # or")
        print("   sudo dnf install java-11-openjdk-devel")
        
    elif system == "Windows":
        print("🪟 Windows Installation:")
        print("   1. Download Oracle JDK: https://www.oracle.com/java/technologies/downloads/")
        print("   2. Or download OpenJDK: https://adoptium.net/")
        print("   3. Run the .msi installer")
        print("   4. Java should be automatically added to PATH")
        
    else:
        print(f"❓ Unknown system: {system}")
        print("   Please install Java from: https://www.oracle.com/java/technologies/downloads/")

def test_convertwithmoss_after_java():
    """Test ConvertWithMoss functionality after Java installation"""
    
    print("\\n🧪 Testing ConvertWithMoss with Java...")
    print("=" * 40)
    
    jar_path = "/Users/marlsz/Documents/GitHub/XPM-version-2/mrhyman.jar"
    
    if not os.path.exists(jar_path):
        print(f"❌ ConvertWithMoss JAR not found: {jar_path}")
        return False
    
    try:
        # Test basic execution
        print("🚀 Testing JAR execution...")
        
        # Try different command line options that might work
        test_commands = [
            ['java', '-jar', jar_path, '--help'],
            ['java', '-jar', jar_path, '-h'],
            ['java', '-jar', jar_path, '--version'],
            ['java', '-jar', jar_path, '-v'],
            ['java', '-jar', jar_path],  # Just run it
        ]
        
        for i, cmd in enumerate(test_commands, 1):
            print(f"\\n  Test {i}: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"  ✅ Success!")
                    if result.stdout:
                        print(f"  Output: {result.stdout[:300]}...")
                    return True
                else:
                    print(f"  ⚠️  Exit code: {result.returncode}")
                    if result.stderr:
                        print(f"  Error: {result.stderr[:200]}...")
                    if result.stdout:
                        print(f"  Output: {result.stdout[:200]}...")
                        
            except subprocess.TimeoutExpired:
                print(f"  ⏰ Timeout (might be waiting for input)")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print("\\n💡 ConvertWithMoss might require specific command line arguments")
        print("   Check the documentation or try running with sample files")
        return False
        
    except Exception as e:
        print(f"❌ Error testing ConvertWithMoss: {e}")
        return False

def show_next_steps():
    """Show next steps for integration"""
    
    print("\\n🎯 Next Steps for ConvertWithMoss Integration:")
    print("=" * 50)
    
    steps = [
        "1. ☕ Install Java runtime (see instructions above)",
        "2. 🧪 Test ConvertWithMoss JAR execution",
        "3. 📖 Study ConvertWithMoss documentation/help output",
        "4. 🔧 Update our Python wrapper with correct command syntax",
        "5. 🎨 Add conversion tab to main XPM tool GUI",
        "6. 🧩 Integrate format conversion into workflow",
        "7. 📚 Test with sample files from different formats",
        "8. 🚀 Deploy multi-format conversion capabilities"
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print("\\n🎉 Once Java is installed, you'll be able to:")
    benefits = [
        "📥 Import Kontakt (.nki), SoundFont (.sf2), SFZ files to XPM",
        "📤 Export XPM files to other popular sampler formats", 
        "🔄 Convert between 15+ different sampler formats",
        "🧠 Learn from professional mapping strategies",
        "⚡ Batch process entire sample libraries",
        "🌐 Share your MPC creations in universal formats"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")

if __name__ == "__main__":
    print("🔧 ConvertWithMoss Setup Guide")
    print("=" * 50)
    
    java_works = check_java_installation()
    
    if not java_works:
        show_installation_instructions()
    else:
        success = test_convertwithmoss_after_java()
        if success:
            print("\\n🎉 ConvertWithMoss is ready to use!")
        else:
            print("\\n🔧 ConvertWithMoss needs additional configuration")
    
    show_next_steps()
