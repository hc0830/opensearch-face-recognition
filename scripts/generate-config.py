#!/usr/bin/env python3
"""
从CloudFormation堆栈输出生成前端配置文件
此脚本读取CDK部署的CloudFormation堆栈输出，并生成包含实际端点URL的配置文件
"""

import boto3
import json
import os
from datetime import datetime


def get_stack_outputs(stack_name, region="ap-southeast-1"):
    """获取CloudFormation堆栈的输出值"""
    cf = boto3.client("cloudformation", region_name=region)

    try:
        response = cf.describe_stacks(StackName=stack_name)
        stack = response["Stacks"][0]

        outputs = {}
        if "Outputs" in stack:
            for output in stack["Outputs"]:
                outputs[output["OutputKey"]] = output["OutputValue"]

        return outputs
    except Exception as e:
        print(f"错误：无法获取堆栈 {stack_name} 的输出: {e}")
        return {}


def generate_config_file(region="ap-southeast-1", environment="prod"):
    """生成配置文件"""

    # 堆栈名称
    stacks = {
        "API": f"OpenSearchFaceRecognition-{environment.title()}-API",
        "FRONTEND": f"OpenSearchFaceRecognition-{environment.title()}-Frontend",
        "LAMBDA": f"OpenSearchFaceRecognition-{environment.title()}-Lambda",
        "OPENSEARCH": f"OpenSearchFaceRecognition-{environment.title()}-OpenSearch",
        "MONITORING": f"OpenSearchFaceRecognition-{environment.title()}-Monitoring",
    }

    # 获取各堆栈的输出
    api_outputs = get_stack_outputs(stacks["API"], region)
    frontend_outputs = get_stack_outputs(stacks["FRONTEND"], region)

    # 提取关键配置值
    config = {
        "API_BASE_URL": api_outputs.get(
            "FaceRecognitionApiEndpoint96103329", ""
        ).rstrip("/"),
        "FRONTEND_URL": frontend_outputs.get("FrontendUrl", ""),
        "CLOUDFRONT_DISTRIBUTION_ID": frontend_outputs.get(
            "CloudFrontDistributionId", ""
        ),
        "CLOUDFRONT_DOMAIN_NAME": frontend_outputs.get("CloudFrontDomainName", ""),
        "FRONTEND_BUCKET_NAME": frontend_outputs.get("FrontendBucketName", ""),
        "REGION": region,
        "ENVIRONMENT": environment,
        "VERSION": "1.0.0",
        "GENERATED_AT": datetime.utcnow().isoformat() + "Z",
        "STACKS": stacks,
    }

    # 生成JavaScript配置文件内容
    js_content = f"""// 面部识别系统配置文件
// 此文件由CDK部署时自动生成，包含CloudFormation输出的实际值
// 生成时间: {config['GENERATED_AT']}

window.FaceRecognitionConfig = {json.dumps(config, indent=4)};

// 验证配置
console.log('Face Recognition System Config Loaded:', window.FaceRecognitionConfig);

// 配置验证
if (!window.FaceRecognitionConfig.API_BASE_URL) {{
    console.error('警告：API_BASE_URL 未配置，请检查CloudFormation堆栈输出');
}}

if (!window.FaceRecognitionConfig.FRONTEND_URL) {{
    console.error('警告：FRONTEND_URL 未配置，请检查CloudFormation堆栈输出');
}}
"""

    return js_content, config


def upload_to_s3(content, bucket_name, key, region="ap-southeast-1"):
    """上传配置文件到S3"""
    s3 = boto3.client("s3", region_name=region)

    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content,
            ContentType="application/javascript",
            CacheControl="no-cache, no-store, must-revalidate",
        )
        print(f"✅ 配置文件已上传到 s3://{bucket_name}/{key}")
        return True
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始生成面部识别系统配置文件...")

    # 生成配置
    js_content, config = generate_config_file()

    # 显示配置信息
    print("\\n📋 生成的配置信息:")
    print(f"  API端点: {config['API_BASE_URL']}")
    print(f"  前端URL: {config['FRONTEND_URL']}")
    print(f"  CloudFront分发ID: {config['CLOUDFRONT_DISTRIBUTION_ID']}")
    print(f"  S3存储桶: {config['FRONTEND_BUCKET_NAME']}")
    print(f"  区域: {config['REGION']}")
    print(f"  环境: {config['ENVIRONMENT']}")

    # 保存到本地文件
    config_file_path = os.path.join(os.path.dirname(__file__), "..", "config.js")
    with open(config_file_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"\\n💾 配置文件已保存到: {config_file_path}")

    # 上传到S3
    if config["FRONTEND_BUCKET_NAME"]:
        print("\\n📤 正在上传配置文件到S3...")
        success = upload_to_s3(
            js_content, config["FRONTEND_BUCKET_NAME"], "config.js", config["REGION"]
        )

        if success:
            print("\\n🎉 配置文件生成和部署完成！")
            print(f"\\n🌐 访问前端: {config['FRONTEND_URL']}")
            print(
                "\\n💡 提示：如果看到缓存的旧版本，请等待CloudFront缓存更新或手动清除缓存"
            )
        else:
            print("\\n⚠️  配置文件生成成功，但上传到S3失败")
    else:
        print("\\n⚠️  未找到S3存储桶名称，跳过上传")

    # 生成JSON格式的配置（用于其他工具）
    json_config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(json_config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\\n📄 JSON配置文件已保存到: {json_config_path}")


if __name__ == "__main__":
    main()
